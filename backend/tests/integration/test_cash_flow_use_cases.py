from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from app.application.ledger.exceptions import AccountNotFoundError, CategoryNotFoundError, CurrencyNotFoundError, InvalidQueryParameterError, QueryPointLimitExceededError
from app.application.ledger.use_cases.cash_flow import get_cash_flow_summary, list_cash_flow_points
from app.domain.ledger.model.financial_event_filter import FinancialEventFilter
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.ledger.unit_of_work import SqliteLedgerUnitOfWork


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class CashFlowUseCasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.database = SqliteDatabase.initialize(Path(self.temporary_directory.name) / "ledger.sqlite", SCHEMA_PATH)
        with self.open_ledger() as unit_of_work:
            unit_of_work.ledger_metadata_repository.create(uuid4(), 1, 10)
            self.currency = unit_of_work.currency_repository.create("Real", "R$", None, 2, "lucide:CircleDollarSign", b"\x10\x20\x30")
            self.account = unit_of_work.account_repository.create("Checking", None, self.currency.uuid, "lucide:WalletCards", b"\x40\x50\x60")
            self.category = unit_of_work.category_repository.create("General", "lucide:Circle", b"\x70\x80\x90", None)
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

    def test_summary_returns_income_expense_and_counts_for_the_filter(self) -> None:
        self.add_movement(100, 50, 2)
        self.add_movement(110, -20, 3)

        summary = get_cash_flow_summary(
            self.open_ledger,
            self.currency.uuid,
            FinancialEventFilter(from_timestamp=100, to_timestamp=200, account_uuid=self.account.uuid, category_uuid=self.category.uuid),
        )

        self.assertEqual(summary.income, 100)
        self.assertEqual(summary.expense, 60)
        self.assertEqual(summary.event_count, 2)
        self.assertEqual(summary.income_movement_count, 1)
        self.assertEqual(summary.expense_movement_count, 1)

    def test_points_cover_the_filter_and_retain_a_short_final_interval(self) -> None:
        self.add_movement(100, 50)
        self.add_movement(250, -20)

        points = list_cash_flow_points(
            self.open_ledger,
            self.currency.uuid,
            FinancialEventFilter(from_timestamp=100, to_timestamp=300),
            150,
            2,
        )

        self.assertEqual([(point.income, point.expense) for point in points], [(50, 0), (0, 20)])

    def test_queries_reject_unknown_filter_relations(self) -> None:
        operations = (
            (CurrencyNotFoundError, lambda: get_cash_flow_summary(self.open_ledger, uuid4(), FinancialEventFilter(from_timestamp=0, to_timestamp=10))),
            (AccountNotFoundError, lambda: get_cash_flow_summary(self.open_ledger, self.currency.uuid, FinancialEventFilter(from_timestamp=0, to_timestamp=10, account_uuid=uuid4()))),
            (CategoryNotFoundError, lambda: get_cash_flow_summary(self.open_ledger, self.currency.uuid, FinancialEventFilter(from_timestamp=0, to_timestamp=10, category_uuid=uuid4()))),
        )

        for expected_error, operation in operations:
            with self.subTest(expected_error=expected_error):
                with self.assertRaises(expected_error):
                    operation()

    def test_points_reject_invalid_width_and_results_above_the_configured_limit(self) -> None:
        filters = FinancialEventFilter(from_timestamp=100, to_timestamp=301)

        with self.assertRaises(InvalidQueryParameterError):
            list_cash_flow_points(self.open_ledger, self.currency.uuid, filters, 0, 100)
        with self.assertRaises(QueryPointLimitExceededError):
            list_cash_flow_points(self.open_ledger, self.currency.uuid, filters, 100, 2)


if __name__ == "__main__":
    unittest.main()
