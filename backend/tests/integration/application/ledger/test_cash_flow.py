import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from app.application.ledger.exceptions import AccountNotFoundError, CategoryNotFoundError, CurrencyNotFoundError, InvalidQueryParameterError, QueryPointLimitExceededError
from app.application.ledger.use_cases.cash_flow import get_cash_flow_sankey, get_cash_flow_summary, list_cash_flow_points
from app.domain.ledger.model.financial_event_filter import FinancialEventFilter
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.ledger.unit_of_work import SqliteLedgerUnitOfWork


SCHEMA_PATH = Path(__file__).resolve().parents[4] / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


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

    def test_sankey_truncates_category_paths_at_the_requested_detail_level(self) -> None:
        with self.open_ledger() as unit_of_work:
            root = unit_of_work.category_repository.create("Root", "lucide:Circle", b"\x11\x22\x33", None)
            child = unit_of_work.category_repository.create("Child", "lucide:Circle", b"\x22\x33\x44", root.uuid)
            leaf = unit_of_work.category_repository.create("Leaf", "lucide:Circle", b"\x33\x44\x55", child.uuid)
            income = unit_of_work.financial_event_repository.create(120, "Income", "TRANSACTION")
            expense = unit_of_work.financial_event_repository.create(130, "Expense", "TRANSACTION")
            unit_of_work.financial_movement_repository.create(income.uuid, self.account.uuid, leaf.uuid, 100, None)
            unit_of_work.financial_movement_repository.create(expense.uuid, self.account.uuid, leaf.uuid, -40, None)
            unit_of_work.commit()

        sankey = get_cash_flow_sankey(
            self.open_ledger,
            self.currency.uuid,
            FinancialEventFilter(from_timestamp=100, to_timestamp=200, account_uuid=self.account.uuid),
            2,
        )

        self.assertEqual((sankey.income, sankey.expense), (100, 40))
        self.assertEqual(sankey.detail_level, 2)
        node_ids = {node.id for node in sankey.nodes}
        self.assertIn(f"income:{root.uuid}", node_ids)
        self.assertIn(f"income:{child.uuid}", node_ids)
        self.assertNotIn(f"income:{leaf.uuid}", node_ids)
        self.assertIn(f"expense:{root.uuid}", node_ids)
        self.assertIn(f"expense:{child.uuid}", node_ids)
        self.assertNotIn(f"expense:{leaf.uuid}", node_ids)
        links = {(link.source, link.target): link.value for link in sankey.links}
        self.assertEqual(links[(f"income:{child.uuid}", f"income:{root.uuid}")], 100)
        self.assertEqual(links[(f"income:{root.uuid}", f"account:{self.account.uuid}")], 100)
        self.assertEqual(links[(f"account:{self.account.uuid}", f"expense:{root.uuid}")], 40)
        self.assertEqual(links[(f"expense:{root.uuid}", f"expense:{child.uuid}")], 40)

    def test_sankey_compacts_columns_when_selected_detail_exceeds_the_used_hierarchy(self) -> None:
        with self.open_ledger() as unit_of_work:
            root = unit_of_work.category_repository.create("Root", "lucide:Circle", b"\x11\x22\x33", None)
            child = unit_of_work.category_repository.create("Child", "lucide:Circle", b"\x22\x33\x44", root.uuid)
            income = unit_of_work.financial_event_repository.create(120, "Income", "TRANSACTION")
            expense = unit_of_work.financial_event_repository.create(130, "Expense", "TRANSACTION")
            unit_of_work.financial_movement_repository.create(income.uuid, self.account.uuid, child.uuid, 100, None)
            unit_of_work.financial_movement_repository.create(expense.uuid, self.account.uuid, child.uuid, -40, None)
            unit_of_work.commit()

        sankey = get_cash_flow_sankey(
            self.open_ledger,
            self.currency.uuid,
            FinancialEventFilter(from_timestamp=100, to_timestamp=200, account_uuid=self.account.uuid),
            5,
        )

        columns = {node.id: node.column for node in sankey.nodes}
        self.assertEqual(columns[f"income:{root.uuid}"], 1)
        self.assertEqual(columns[f"income:{child.uuid}"], 0)
        self.assertEqual(columns[f"account:{self.account.uuid}"], 2)
        self.assertEqual(columns[f"expense:{root.uuid}"], 3)
        self.assertEqual(columns[f"expense:{child.uuid}"], 4)

    def test_sankey_rejects_invalid_detail_level_and_unknown_scope_relations(self) -> None:
        filters = FinancialEventFilter(from_timestamp=100, to_timestamp=200)
        with self.assertRaises(InvalidQueryParameterError):
            get_cash_flow_sankey(self.open_ledger, self.currency.uuid, filters, 0)
        with self.assertRaises(CurrencyNotFoundError):
            get_cash_flow_sankey(self.open_ledger, uuid4(), filters, 1)
        with self.assertRaises(AccountNotFoundError):
            get_cash_flow_sankey(
                self.open_ledger,
                self.currency.uuid,
                filters.model_copy(update={"account_uuid": uuid4()}),
                1,
            )

    def test_empty_sankey_has_no_scope_node_or_links(self) -> None:
        sankey = get_cash_flow_sankey(
            self.open_ledger,
            self.currency.uuid,
            FinancialEventFilter(from_timestamp=100, to_timestamp=200),
            1,
        )

        self.assertEqual((sankey.income, sankey.expense), (0, 0))
        self.assertEqual(sankey.nodes, [])
        self.assertEqual(sankey.links, [])

    def test_sankey_uses_currency_scope_and_excludes_transfers_without_account_filter(self) -> None:
        with self.open_ledger() as unit_of_work:
            other_account = unit_of_work.account_repository.create("Savings", None, self.currency.uuid, "lucide:WalletCards", b"\x41\x51\x61")
            income = unit_of_work.financial_event_repository.create(120, "Income", "TRANSACTION")
            expense = unit_of_work.financial_event_repository.create(130, "Expense", "TRANSACTION")
            transfer = unit_of_work.financial_event_repository.create(140, "Transfer", "ACCOUNT_TRANSFER")
            unit_of_work.financial_movement_repository.create(income.uuid, self.account.uuid, self.category.uuid, 100, None)
            unit_of_work.financial_movement_repository.create(expense.uuid, other_account.uuid, self.category.uuid, -40, None)
            unit_of_work.financial_movement_repository.create(transfer.uuid, self.account.uuid, self.category.uuid, -500, None)
            unit_of_work.financial_movement_repository.create(transfer.uuid, other_account.uuid, self.category.uuid, 500, None)
            unit_of_work.commit()

        sankey = get_cash_flow_sankey(
            self.open_ledger,
            self.currency.uuid,
            FinancialEventFilter(from_timestamp=100, to_timestamp=200),
            1,
        )

        self.assertIsNone(sankey.account_uuid)
        self.assertEqual((sankey.income, sankey.expense), (100, 40))
        scope = next(node for node in sankey.nodes if node.side == "scope")
        self.assertEqual((scope.id, scope.kind, scope.label), (f"currency:{self.currency.uuid}", "currency", self.currency.name))

    def test_sankey_account_filter_includes_its_side_of_transfers(self) -> None:
        with self.open_ledger() as unit_of_work:
            other_account = unit_of_work.account_repository.create("Savings", None, self.currency.uuid, "lucide:WalletCards", b"\x41\x51\x61")
            transfer = unit_of_work.financial_event_repository.create(140, "Transfer", "ACCOUNT_TRANSFER")
            unit_of_work.financial_movement_repository.create(transfer.uuid, self.account.uuid, self.category.uuid, -100, None)
            unit_of_work.financial_movement_repository.create(transfer.uuid, other_account.uuid, self.category.uuid, 100, None)
            unit_of_work.commit()

        source = get_cash_flow_sankey(
            self.open_ledger,
            self.currency.uuid,
            FinancialEventFilter(from_timestamp=100, to_timestamp=200, account_uuid=self.account.uuid),
            1,
        )
        destination = get_cash_flow_sankey(
            self.open_ledger,
            self.currency.uuid,
            FinancialEventFilter(from_timestamp=100, to_timestamp=200, account_uuid=other_account.uuid),
            1,
        )

        self.assertEqual((source.income, source.expense), (0, 100))
        self.assertEqual((destination.income, destination.expense), (100, 0))
        self.assertEqual(source.account_uuid, self.account.uuid)
        self.assertEqual(destination.account_uuid, other_account.uuid)

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
