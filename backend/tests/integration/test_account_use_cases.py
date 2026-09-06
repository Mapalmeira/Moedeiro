from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.application.ledger.exceptions import AccountInUseError, AccountNameUnavailableError, AccountNotFoundError, CurrencyNotFoundError
from app.application.ledger.use_cases.account import create_account, delete_account, get_account, list_accounts, update_account
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.ledger.unit_of_work import SqliteLedgerUnitOfWork


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class AccountUseCasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.database = SqliteDatabase.initialize(Path(self.temporary_directory.name) / "ledger.sqlite", SCHEMA_PATH)
        with self.open_ledger() as unit_of_work:
            unit_of_work.ledger_metadata_repository.create(uuid4(), 1, 10)
            self.currency = unit_of_work.currency_repository.create("Real", "R$", None, 2, "lucide:CircleDollarSign", b"\x10\x20\x30")
            unit_of_work.commit()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def open_ledger(self) -> SqliteLedgerUnitOfWork:
        return SqliteLedgerUnitOfWork(self.database)

    def create(self, name: str = "Checking"):
        return create_account(self.open_ledger, name, "Daily account", self.currency.uuid, "lucide:WalletCards", b"\x40\x50\x60")

    def test_create_commits_and_returns_the_persisted_account(self) -> None:
        account = self.create()

        self.assertEqual(get_account(self.open_ledger, account.uuid), account)

    def test_create_rejects_an_unknown_currency(self) -> None:
        with self.assertRaises(CurrencyNotFoundError):
            create_account(self.open_ledger, "Checking", None, uuid4(), "lucide:WalletCards", b"\x40\x50\x60")

        self.assertEqual(list_accounts(self.open_ledger), [])

    def test_create_rejects_an_unavailable_name(self) -> None:
        self.create()

        with self.assertRaises(AccountNameUnavailableError):
            self.create()

    def test_create_rejects_invalid_data_without_persisting_it(self) -> None:
        with self.assertRaises(ValidationError):
            create_account(self.open_ledger, "", None, self.currency.uuid, "lucide:WalletCards", b"\x40\x50\x60")

        self.assertEqual(list_accounts(self.open_ledger), [])

    def test_get_raises_for_an_unknown_account(self) -> None:
        with self.assertRaises(AccountNotFoundError):
            get_account(self.open_ledger, uuid4())

    def test_list_returns_every_item_in_insertion_order(self) -> None:
        created = [self.create(name) for name in ("Charlie", "Alpha", "Bravo")]
        self.assertEqual(list_accounts(self.open_ledger), created)

    def test_update_changes_mutable_fields_but_preserves_currency(self) -> None:
        account = self.create()

        updated = update_account(self.open_ledger, account.uuid, "Savings", None, "lucide:PiggyBank", b"\xaa\xbb\xcc")

        self.assertEqual(updated.name, "Savings")
        self.assertIsNone(updated.note)
        self.assertEqual(updated.icon, "lucide:PiggyBank")
        self.assertEqual(updated.color_code, b"\xaa\xbb\xcc")
        self.assertEqual(updated.currency_uuid, account.currency_uuid)
        self.assertEqual(get_account(self.open_ledger, account.uuid), updated)

    def test_update_rejects_an_unknown_account_or_unavailable_name(self) -> None:
        existing = self.create("Existing")
        other = self.create("Other")

        with self.assertRaises(AccountNotFoundError):
            update_account(self.open_ledger, uuid4(), "Missing", None, "lucide:WalletCards", b"\x40\x50\x60")
        with self.assertRaises(AccountNameUnavailableError):
            update_account(self.open_ledger, other.uuid, existing.name, None, "lucide:WalletCards", b"\x40\x50\x60")

        self.assertEqual(get_account(self.open_ledger, other.uuid), other)

    def test_delete_removes_an_unused_account(self) -> None:
        account = self.create()

        self.assertIsNone(delete_account(self.open_ledger, account.uuid))

        with self.assertRaises(AccountNotFoundError):
            get_account(self.open_ledger, account.uuid)

    def test_delete_rejects_an_account_used_by_a_financial_movement(self) -> None:
        account = self.create()
        with self.open_ledger() as unit_of_work:
            category = unit_of_work.category_repository.create("Food", "lucide:Utensils", b"\x80\x80\x80", None)
            event = unit_of_work.financial_event_repository.create(20, "Lunch", "TRANSACTION")
            unit_of_work.financial_movement_repository.create(event.uuid, account.uuid, category.uuid, -100, None)
            unit_of_work.commit()

        with self.assertRaises(AccountInUseError):
            delete_account(self.open_ledger, account.uuid)

        self.assertEqual(get_account(self.open_ledger, account.uuid), account)

    def test_delete_rejects_an_account_selected_by_a_budget(self) -> None:
        account = self.create()
        with self.open_ledger() as unit_of_work:
            category = unit_of_work.category_repository.create("Food", "lucide:Utensils", b"\x80\x80\x80", None)
            budget = unit_of_work.budget_repository.create(category.uuid, self.currency.uuid, 20, 30, "Monthly", "Food budget", 100, "lucide:ReceiptText", b"\x80\x80\x80")
            unit_of_work.budget_repository.add_account(budget.uuid, account.uuid)
            unit_of_work.commit()

        with self.assertRaises(AccountInUseError):
            delete_account(self.open_ledger, account.uuid)

        self.assertEqual(get_account(self.open_ledger, account.uuid), account)

    def test_delete_rejects_an_unknown_account(self) -> None:
        with self.assertRaises(AccountNotFoundError):
            delete_account(self.open_ledger, uuid4())

if __name__ == "__main__":
    unittest.main()
