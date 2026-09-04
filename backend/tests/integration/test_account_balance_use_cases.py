from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from app.application.ledger.exceptions import AccountNotFoundError
from app.application.ledger.use_cases.account_balance import get_account_balance, list_account_balance_points
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.ledger.unit_of_work import SqliteLedgerUnitOfWork


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class AccountBalanceUseCasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.database = SqliteDatabase.initialize(Path(self.temporary_directory.name) / "ledger.sqlite", SCHEMA_PATH)
        with self.open_ledger() as unit_of_work:
            unit_of_work.ledger_metadata_repository.create(uuid4(), 1, 10)
            self.currency = unit_of_work.currency_repository.create("Real", "R$", None, 2, "CircleDollarSign", b"\x10\x20\x30")
            self.account = unit_of_work.account_repository.create("Checking", None, self.currency.uuid, "WalletCards", b"\x40\x50\x60")
            self.category = unit_of_work.category_repository.create("General", "Circle", b"\x70\x80\x90", None)
            unit_of_work.commit()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def open_ledger(self) -> SqliteLedgerUnitOfWork:
        return SqliteLedgerUnitOfWork(self.database)

    def add_movement(self, occurred_at: int, value: int, quantity: int = 1) -> None:
        with self.open_ledger() as unit_of_work:
            event = unit_of_work.financial_event_repository.create(occurred_at, "Movement", "TRANSACTION")
            unit_of_work.financial_movement_repository.create(event.uuid, self.account.uuid, self.category.uuid, value, None, quantity)
            unit_of_work.commit()

    def test_get_balance_returns_the_account_balance_at_the_inclusive_timestamp(self) -> None:
        self.add_movement(10, 100)
        self.add_movement(20, -15, 2)
        self.add_movement(30, 500)

        self.assertEqual(get_account_balance(self.open_ledger, self.account.uuid, 20), 70)

    def test_list_points_returns_closing_balances_for_the_requested_intervals(self) -> None:
        self.add_movement(50, 100)
        self.add_movement(105, -20)
        self.add_movement(120, 30)

        points = list_account_balance_points(self.open_ledger, self.account.uuid, 100, 3, 10, 3)

        self.assertEqual(points, [80, 80, 110])

    def test_queries_translate_an_unknown_account_to_the_application_error(self) -> None:
        account_uuid = uuid4()

        with self.assertRaises(AccountNotFoundError):
            get_account_balance(self.open_ledger, account_uuid, 10)
        with self.assertRaises(AccountNotFoundError):
            list_account_balance_points(self.open_ledger, account_uuid, 10, 1, 10, 100)

    def test_list_points_rejects_invalid_dimensions_and_the_configured_limit(self) -> None:
        for point_count, point_interval, max_points in ((0, 10, 100), (1, 0, 100), (4, 10, 3)):
            with self.subTest(point_count=point_count, point_interval=point_interval, max_points=max_points):
                with self.assertRaises(ValueError):
                    list_account_balance_points(self.open_ledger, self.account.uuid, 100, point_count, point_interval, max_points)


if __name__ == "__main__":
    unittest.main()
