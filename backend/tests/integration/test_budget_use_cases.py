from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.application.ledger.exceptions import AccountNotFoundError, BudgetAccountCurrencyMismatchError, BudgetNameUnavailableError, BudgetNotActiveError, BudgetNotFoundError, CategoryNotFoundError, CurrencyNotFoundError
from app.application.ledger.use_cases.budget import _require_accounts_in_currency, create_budget, delete_budget, get_budget, list_budget_page, update_budget
from app.application.ledger.use_cases.budget_status import get_budget_status, list_budget_status_page
from app.domain.ledger.model.budget import MAX_BUDGET_ACCOUNTS
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.ledger.unit_of_work import SqliteLedgerUnitOfWork


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class BudgetUseCasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.database = SqliteDatabase.initialize(Path(self.temporary_directory.name) / "ledger.sqlite", SCHEMA_PATH)
        with self.open_ledger() as unit_of_work:
            unit_of_work.ledger_metadata_repository.create(uuid4(), 1, 10)
            self.currency = unit_of_work.currency_repository.create("Real", "R$", None, 2, "CircleDollarSign", b"\x10\x20\x30")
            self.other_currency = unit_of_work.currency_repository.create("Dollar", "$", None, 2, "CircleDollarSign", b"\x20\x30\x40")
            self.category = unit_of_work.category_repository.create("Food", "Utensils", b"\x70\x80\x90", None)
            self.other_category = unit_of_work.category_repository.create("Leisure", "Gamepad2", b"\x80\x90\xa0", None)
            self.account = unit_of_work.account_repository.create("Checking", None, self.currency.uuid, "WalletCards", b"\x40\x50\x60")
            self.second_account = unit_of_work.account_repository.create("Savings", None, self.currency.uuid, "PiggyBank", b"\x50\x60\x70")
            self.other_currency_account = unit_of_work.account_repository.create("Dollar", None, self.other_currency.uuid, "WalletCards", b"\x60\x70\x80")
            unit_of_work.commit()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def open_ledger(self) -> SqliteLedgerUnitOfWork:
        return SqliteLedgerUnitOfWork(self.database)

    def create(self, name: str = "Monthly", account_uuids=()):
        return create_budget(
            self.open_ledger,
            self.category.uuid,
            self.currency.uuid,
            10,
            20,
            name,
            "Monthly spending",
            100,
            "ReceiptText",
            b"\x80\x80\x80",
            account_uuids,
        )

    def test_create_commits_and_returns_account_selectors(self) -> None:
        budget = self.create(account_uuids=[self.second_account.uuid, self.account.uuid, self.account.uuid])

        self.assertEqual(get_budget(self.open_ledger, budget.uuid), budget)
        self.assertEqual(budget.account_uuids, sorted((self.account.uuid, self.second_account.uuid), key=lambda value: value.bytes))

    def test_create_without_accounts_keeps_the_all_currency_accounts_scope(self) -> None:
        budget = self.create()

        self.assertEqual(budget.account_uuids, [])

    def test_create_rejects_unknown_relations_or_an_account_in_another_currency(self) -> None:
        operations = (
            (CurrencyNotFoundError, lambda: create_budget(self.open_ledger, self.category.uuid, uuid4(), 10, 20, "Currency", "Description", 100, "Circle", b"\x10\x20\x30", [])),
            (CategoryNotFoundError, lambda: create_budget(self.open_ledger, uuid4(), self.currency.uuid, 10, 20, "Category", "Description", 100, "Circle", b"\x10\x20\x30", [])),
            (AccountNotFoundError, lambda: create_budget(self.open_ledger, self.category.uuid, self.currency.uuid, 10, 20, "Account", "Description", 100, "Circle", b"\x10\x20\x30", [uuid4()])),
            (BudgetAccountCurrencyMismatchError, lambda: create_budget(self.open_ledger, self.category.uuid, self.currency.uuid, 10, 20, "Mismatch", "Description", 100, "Circle", b"\x10\x20\x30", [self.other_currency_account.uuid])),
        )

        for expected_error, operation in operations:
            with self.subTest(expected_error=expected_error):
                with self.assertRaises(expected_error):
                    operation()

        self.assertEqual(list_budget_page(self.open_ledger, 1, 200, "name", True), [])

    def test_create_rejects_an_unavailable_name_or_invalid_data(self) -> None:
        self.create()

        with self.assertRaises(BudgetNameUnavailableError):
            self.create()
        with self.assertRaises(ValidationError):
            create_budget(self.open_ledger, self.category.uuid, self.currency.uuid, 20, 10, "Invalid", "Description", 100, "Circle", b"\x10\x20\x30", [])

        self.assertEqual(len(list_budget_page(self.open_ledger, 1, 200, "name", True)), 1)

    def test_create_rejects_more_than_twenty_account_selectors_before_looking_them_up(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot select more than 50 accounts"):
            self.create(account_uuids=[uuid4() for _ in range(MAX_BUDGET_ACCOUNTS + 1)])

        self.assertEqual(list_budget_page(self.open_ledger, 1, 200, "name", True), [])

    def test_create_validates_selected_accounts_with_one_lookup_query(self) -> None:
        with self.open_ledger() as unit_of_work:
            accounts = [
                unit_of_work.account_repository.create(f"Account {index}", None, self.currency.uuid, "WalletCards", b"\x40\x50\x60")
                for index in range(3)
            ]
            unit_of_work.commit()

        statements: list[str] = []
        with self.open_ledger() as unit_of_work:
            unit_of_work.connection.set_trace_callback(statements.append)
            try:
                _require_accounts_in_currency(unit_of_work, [account.uuid for account in accounts], self.currency.uuid)
            finally:
                unit_of_work.connection.set_trace_callback(None)

        account_selects = [statement for statement in statements if "FROM account WHERE uuid IN" in statement]
        self.assertEqual(len(account_selects), 1)

    def test_get_and_delete_reject_an_unknown_budget(self) -> None:
        for operation in (lambda: get_budget(self.open_ledger, uuid4()), lambda: delete_budget(self.open_ledger, uuid4())):
            with self.subTest(operation=operation):
                with self.assertRaises(BudgetNotFoundError):
                    operation()

    def test_list_page_applies_ordering_and_pagination(self) -> None:
        charlie = self.create("Charlie")
        alpha = self.create("Alpha")
        bravo = self.create("Bravo")

        self.assertEqual(list_budget_page(self.open_ledger, 1, 2, "name", True), [alpha, bravo])
        self.assertEqual(list_budget_page(self.open_ledger, 1, 1, "name", False), [charlie])

    def test_update_changes_mutable_fields_and_account_scope_but_preserves_currency(self) -> None:
        budget = self.create(account_uuids=[self.account.uuid])

        updated = update_budget(
            self.open_ledger,
            budget.uuid,
            self.other_category.uuid,
            20,
            30,
            "Updated",
            "Updated spending",
            250,
            "Landmark",
            b"\xaa\xbb\xcc",
            [self.second_account.uuid],
        )

        self.assertEqual(updated.category_uuid, self.other_category.uuid)
        self.assertEqual(updated.currency_uuid, budget.currency_uuid)
        self.assertEqual(updated.from_timestamp, 20)
        self.assertEqual(updated.to_timestamp, 30)
        self.assertEqual(updated.name, "Updated")
        self.assertEqual(updated.amount, 250)
        self.assertEqual(updated.account_uuids, [self.second_account.uuid])
        self.assertEqual(get_budget(self.open_ledger, budget.uuid), updated)

    def test_update_rejects_invalid_relations_and_an_unavailable_name_without_partial_changes(self) -> None:
        budget = self.create("Original", [self.account.uuid])
        self.create("Existing")

        operations = (
            (CategoryNotFoundError, lambda: update_budget(self.open_ledger, budget.uuid, uuid4(), 20, 30, "Changed", "Changed", 200, "Circle", b"\x10\x20\x30", [])),
            (AccountNotFoundError, lambda: update_budget(self.open_ledger, budget.uuid, self.category.uuid, 20, 30, "Changed", "Changed", 200, "Circle", b"\x10\x20\x30", [uuid4()])),
            (BudgetAccountCurrencyMismatchError, lambda: update_budget(self.open_ledger, budget.uuid, self.category.uuid, 20, 30, "Changed", "Changed", 200, "Circle", b"\x10\x20\x30", [self.other_currency_account.uuid])),
            (BudgetNameUnavailableError, lambda: update_budget(self.open_ledger, budget.uuid, self.category.uuid, 20, 30, "Existing", "Changed", 200, "Circle", b"\x10\x20\x30", [])),
        )

        for expected_error, operation in operations:
            with self.subTest(expected_error=expected_error):
                with self.assertRaises(expected_error):
                    operation()

        self.assertEqual(get_budget(self.open_ledger, budget.uuid), budget)

    def test_delete_removes_the_budget(self) -> None:
        budget = self.create(account_uuids=[self.account.uuid])

        self.assertIsNone(delete_budget(self.open_ledger, budget.uuid))

        with self.assertRaises(BudgetNotFoundError):
            get_budget(self.open_ledger, budget.uuid)

    def test_get_status_returns_aggregated_expenses_for_an_active_budget(self) -> None:
        budget = self.create(account_uuids=[self.account.uuid])
        with self.open_ledger() as unit_of_work:
            event = unit_of_work.financial_event_repository.create(15, "Groceries", "SHOPPING_LIST")
            unit_of_work.financial_movement_repository.create(event.uuid, self.account.uuid, self.category.uuid, -30, "Item", 2)
            unit_of_work.commit()

        budget_status = get_budget_status(self.open_ledger, budget.uuid, 15)

        self.assertEqual(budget_status.spent_amount, 60)
        self.assertFalse(budget_status.over_budget)

    def test_get_status_distinguishes_missing_and_inactive_budgets(self) -> None:
        budget = self.create()

        with self.assertRaises(BudgetNotFoundError):
            get_budget_status(self.open_ledger, uuid4(), 15)
        with self.assertRaises(BudgetNotActiveError):
            get_budget_status(self.open_ledger, budget.uuid, 20)

    def test_list_status_page_returns_active_budgets_in_name_order(self) -> None:
        monthly = self.create("Monthly")
        alpha = self.create("Alpha")

        first_page = list_budget_status_page(self.open_ledger, 15, 1, 1)
        second_page = list_budget_status_page(self.open_ledger, 15, 2, 1)

        self.assertEqual([status.budget_uuid for status in first_page], [alpha.uuid])
        self.assertEqual([status.budget_uuid for status in second_page], [monthly.uuid])


if __name__ == "__main__":
    unittest.main()
