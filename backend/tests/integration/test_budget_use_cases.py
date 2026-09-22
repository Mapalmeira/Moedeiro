import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

from pydantic import ValidationError

from app.application.ledger.exceptions import AccountNotFoundError, BudgetLimitReachedError, BudgetNameUnavailableError, BudgetNotFoundError, CategoryNotFoundError, CurrencyNotFoundError
from app.application.ledger.use_cases.budget import create_budget, delete_budget, get_budget, update_budget
from app.application.ledger.use_cases.budget_overview import list_budget_overview, list_budgets_for_currency
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.ledger.unit_of_work import SqliteLedgerUnitOfWork


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class BudgetUseCasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.database = SqliteDatabase.initialize(Path(self.temporary_directory.name) / "ledger.sqlite", SCHEMA_PATH)
        with self.open_ledger() as unit_of_work:
            unit_of_work.ledger_metadata_repository.create(uuid4(), 1, 10)
            self.currency = unit_of_work.currency_repository.create("Real", "R$", None, 2, "lucide:CircleDollarSign", b"\x10\x20\x30")
            self.category = unit_of_work.category_repository.create("Food", "lucide:Utensils", b"\x70\x80\x90", None)
            self.other_category = unit_of_work.category_repository.create("Leisure", "lucide:Gamepad2", b"\x80\x90\xa0", None)
            self.account = unit_of_work.account_repository.create("Checking", None, self.currency.uuid, "lucide:WalletCards", b"\x40\x50\x60")
            self.second_account = unit_of_work.account_repository.create("Savings", None, self.currency.uuid, "lucide:PiggyBank", b"\x50\x60\x70")
            unit_of_work.commit()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def open_ledger(self) -> SqliteLedgerUnitOfWork:
        return SqliteLedgerUnitOfWork(self.database)

    def create(self, name: str = "Monthly", account_uuid=None, from_timestamp: int = 10, to_timestamp: int = 20, amount: int = 100):
        return create_budget(
            self.open_ledger,
            account_uuid or self.account.uuid,
            self.category.uuid,
            from_timestamp,
            to_timestamp,
            name,
            "Monthly spending",
            amount,
        )

    def test_create_commits_one_account_relation(self) -> None:
        budget = self.create()
        self.assertEqual(get_budget(self.open_ledger, budget.uuid), budget)
        self.assertEqual(budget.account_uuid, self.account.uuid)

    def test_creation_limit_can_be_reused_after_deletion(self) -> None:
        with patch("app.application.ledger.use_cases.budget.MAXIMUM_BUDGETS", 1):
            budget = self.create("First")
            with self.assertRaises(BudgetLimitReachedError):
                self.create("Overflow")
            delete_budget(self.open_ledger, budget.uuid)
            replacement = self.create("Replacement")
        self.assertEqual(get_budget(self.open_ledger, replacement.uuid), replacement)

    def test_create_rejects_unknown_account_category_duplicate_name_and_invalid_period(self) -> None:
        operations = (
            (AccountNotFoundError, lambda: create_budget(self.open_ledger, uuid4(), self.category.uuid, 10, 20, "Account", "Description", 100)),
            (CategoryNotFoundError, lambda: create_budget(self.open_ledger, self.account.uuid, uuid4(), 10, 20, "Category", "Description", 100)),
        )
        for expected_error, operation in operations:
            with self.subTest(expected_error=expected_error):
                with self.assertRaises(expected_error):
                    operation()
        self.create("Existing")
        with self.assertRaises(BudgetNameUnavailableError):
            self.create("Existing")
        with self.assertRaises(ValidationError):
            create_budget(self.open_ledger, self.account.uuid, self.category.uuid, 20, 10, "Invalid", "Description", 100)

    def test_update_changes_mutable_fields_and_preserves_account(self) -> None:
        budget = self.create()
        updated = update_budget(
            self.open_ledger,
            budget.uuid,
            self.other_category.uuid,
            20,
            30,
            "Updated",
            "Updated spending",
            250,
        )
        self.assertEqual(updated.account_uuid, budget.account_uuid)
        self.assertEqual(updated.category_uuid, self.other_category.uuid)
        self.assertEqual(updated.name, "Updated")
        self.assertEqual(get_budget(self.open_ledger, budget.uuid), updated)

    def test_update_rejects_unknown_budget_category_and_duplicate_name_without_partial_changes(self) -> None:
        budget = self.create("Original")
        self.create("Existing", self.second_account.uuid)
        with self.assertRaises(BudgetNotFoundError):
            update_budget(self.open_ledger, uuid4(), self.category.uuid, 20, 30, "Changed", "Changed", 200)
        with self.assertRaises(CategoryNotFoundError):
            update_budget(self.open_ledger, budget.uuid, uuid4(), 20, 30, "Changed", "Changed", 200)
        with self.assertRaises(BudgetNameUnavailableError):
            update_budget(self.open_ledger, budget.uuid, self.category.uuid, 20, 30, "Existing", "Changed", 200)
        self.assertEqual(get_budget(self.open_ledger, budget.uuid), budget)

    def test_overview_and_currency_listing_delegate_to_read_model(self) -> None:
        active_budget = self.create("Active", from_timestamp=10, to_timestamp=30)
        future = self.create("Future", self.second_account.uuid, 30, 40)
        overview = list_budget_overview(self.open_ledger, 20, ("ACTIVE", "FUTURE"), None, None, None, 10, None, None)
        currency_items = list_budgets_for_currency(self.open_ledger, 20, self.currency.uuid, 3)
        self.assertEqual({item.budget.uuid for item in overview}, {active_budget.uuid, future.uuid})
        self.assertEqual([item.budget.uuid for item in currency_items], [active_budget.uuid])
        with self.assertRaises(AccountNotFoundError):
            list_budget_overview(self.open_ledger, 20, ("ACTIVE",), uuid4(), None, None, 10, None, None)
        with self.assertRaises(CategoryNotFoundError):
            list_budget_overview(self.open_ledger, 20, ("ACTIVE",), None, uuid4(), None, 10, None, None)
        with self.assertRaises(CurrencyNotFoundError):
            list_budgets_for_currency(self.open_ledger, 20, uuid4(), 3)

    def test_delete_removes_budget_and_unknown_budget_is_rejected(self) -> None:
        budget = self.create()
        delete_budget(self.open_ledger, budget.uuid)
        with self.assertRaises(BudgetNotFoundError):
            get_budget(self.open_ledger, budget.uuid)
        with self.assertRaises(BudgetNotFoundError):
            delete_budget(self.open_ledger, uuid4())
