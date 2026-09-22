import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from pydantic import ValidationError

from app.application.ledger.exceptions import CurrencyInUseError, CurrencyNameUnavailableError, CurrencyNotFoundError
from app.application.ledger.use_cases.currency import create_currency, delete_currency, get_currency, list_currencies, update_currency
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.ledger.unit_of_work import SqliteLedgerUnitOfWork


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class CurrencyUseCasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.database = SqliteDatabase.initialize(
            Path(self.temporary_directory.name) / "ledger.sqlite",
            SCHEMA_PATH,
        )
        with self.open_ledger() as unit_of_work:
            unit_of_work.ledger_metadata_repository.create(uuid4(), 1, 10)
            unit_of_work.commit()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def open_ledger(self) -> SqliteLedgerUnitOfWork:
        return SqliteLedgerUnitOfWork(self.database)

    def create(self, name="Real"):
        return create_currency(
            self.open_ledger,
            name,
            "R$",
            None,
            2,
            "lucide:CircleDollarSign",
            b"\x10\x20\x30",
        )

    def test_create_commits_and_returns_the_persisted_currency(self) -> None:
        currency = self.create()

        self.assertEqual(get_currency(self.open_ledger, currency.uuid), currency)

    def test_create_rejects_invalid_data_without_persisting_it(self) -> None:
        with self.assertRaises(ValidationError):
            create_currency(
                self.open_ledger,
                "",
                None,
                None,
                2,
                "lucide:CircleDollarSign",
                b"\x10\x20\x30",
            )

        self.assertEqual(list_currencies(self.open_ledger), [])

    def test_create_rejects_an_unavailable_name(self) -> None:
        self.create("Real")

        with self.assertRaises(CurrencyNameUnavailableError):
            self.create("Real")

        self.assertEqual([currency.name for currency in list_currencies(self.open_ledger)], ["Real"])

    def test_get_raises_for_an_unknown_currency(self) -> None:
        with self.assertRaises(CurrencyNotFoundError):
            get_currency(self.open_ledger, uuid4())

    def test_list_returns_every_item_in_insertion_order(self) -> None:
        created = [self.create(name) for name in ("Charlie", "Alpha", "Bravo")]
        self.assertEqual(list_currencies(self.open_ledger), created)

    def test_update_changes_mutable_fields_but_preserves_decimal_places(self) -> None:
        currency = self.create()

        updated = update_currency(
            self.open_ledger,
            currency.uuid,
            "Brazilian Real",
            None,
            " BRL",
            "lucide:Banknote",
            b"\xaa\xbb\xcc",
        )

        self.assertEqual(updated.name, "Brazilian Real")
        self.assertIsNone(updated.prefix)
        self.assertEqual(updated.suffix, " BRL")
        self.assertEqual(updated.icon, "lucide:Banknote")
        self.assertEqual(updated.color_code, b"\xaa\xbb\xcc")
        self.assertEqual(updated.decimal_places, currency.decimal_places)
        self.assertEqual(get_currency(self.open_ledger, currency.uuid), updated)

    def test_update_rejects_unknown_currency(self) -> None:
        with self.assertRaises(CurrencyNotFoundError):
            update_currency(
                self.open_ledger,
                uuid4(),
                "Real",
                "R$",
                None,
                "lucide:Banknote",
                b"\xaa\xbb\xcc",
            )

    def test_update_rejects_an_unavailable_name(self) -> None:
        first = self.create("Real")
        second = self.create("Dolár")

        with self.assertRaises(CurrencyNameUnavailableError):
            update_currency(
                self.open_ledger,
                second.uuid,
                first.name,
                "$",
                None,
                "lucide:Banknote",
                b"\xaa\xbb\xcc",
            )

        self.assertEqual(get_currency(self.open_ledger, second.uuid), second)

    def test_delete_removes_an_unused_currency(self) -> None:
        currency = self.create()

        result = delete_currency(self.open_ledger, currency.uuid)

        self.assertIsNone(result)
        with self.assertRaises(CurrencyNotFoundError):
            get_currency(self.open_ledger, currency.uuid)

    def test_delete_rejects_a_currency_used_by_an_account(self) -> None:
        currency = self.create()
        with self.open_ledger() as unit_of_work:
            unit_of_work.account_repository.create(
                "Checking",
                None,
                currency.uuid,
                "lucide:WalletCards",
                b"\x80\x80\x80",
            )
            unit_of_work.commit()

        with self.assertRaises(CurrencyInUseError):
            delete_currency(self.open_ledger, currency.uuid)

        self.assertEqual(get_currency(self.open_ledger, currency.uuid), currency)

    def test_delete_rejects_a_currency_used_by_a_budget(self) -> None:
        currency = self.create()
        with self.open_ledger() as unit_of_work:
            category = unit_of_work.category_repository.create(
                "Food",
                "lucide:Utensils",
                b"\x80\x80\x80",
                None,
            )
            account = unit_of_work.account_repository.create(
                "Budget account", None, currency.uuid, "lucide:WalletCards", b"\x80\x80\x80"
            )
            unit_of_work.budget_repository.create(
                account.uuid,
                category.uuid,
                10,
                20,
                "Monthly",
                "Monthly food budget",
                100,
            )
            unit_of_work.commit()

        with self.assertRaises(CurrencyInUseError):
            delete_currency(self.open_ledger, currency.uuid)

        self.assertEqual(get_currency(self.open_ledger, currency.uuid), currency)

    def test_delete_rejects_an_unknown_currency(self) -> None:
        with self.assertRaises(CurrencyNotFoundError):
            delete_currency(self.open_ledger, uuid4())
