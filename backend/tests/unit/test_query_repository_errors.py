import sqlite3
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from app.application.ledger.exceptions import QueryResultOverflowError
from app.domain.ledger.model.financial_event_filter import FinancialEventFilter
from app.infrastructure.persistence.sqlite.ledger.repository.budget_overview_query import SqliteBudgetOverviewQueryRepository
from app.infrastructure.persistence.sqlite.ledger.repository.cash_flow_query import SqliteCashFlowQueryRepository


class QueryRepositoryErrorsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = MagicMock()
        self.connection.execute.side_effect = sqlite3.OperationalError("integer overflow")
        self.uuid = uuid4()
        self.filters = FinancialEventFilter(from_timestamp=0, to_timestamp=10)

    def test_budget_overview_queries_translate_integer_overflow(self) -> None:
        repository = SqliteBudgetOverviewQueryRepository(self.connection)

        with self.assertRaises(QueryResultOverflowError):
            repository.list_page(5, ["ACTIVE"], None, None, None, 10, None, None)
        with self.assertRaises(QueryResultOverflowError):
            repository.list_for_currency(5, self.uuid, 10)

    def test_budget_overview_rejects_incomplete_cursor_and_skips_empty_states(self) -> None:
        repository = SqliteBudgetOverviewQueryRepository(self.connection)

        self.assertEqual(repository.list_page(5, [], None, None, None, 10, None, None), [])
        for cursor_name, cursor_uuid in (("Budget", None), (None, self.uuid)):
            with self.subTest(cursor_name=cursor_name, cursor_uuid=cursor_uuid):
                with self.assertRaisesRegex(ValueError, "cursor name and UUID must be provided together"):
                    repository.list_page(5, ["ACTIVE"], None, None, None, 10, cursor_name, cursor_uuid)

    def test_cash_flow_queries_translate_integer_overflow(self) -> None:
        repository = SqliteCashFlowQueryRepository(self.connection)

        with self.assertRaises(QueryResultOverflowError):
            repository.get_summary(self.uuid, self.filters)
        with self.assertRaises(QueryResultOverflowError):
            repository.list_points(self.uuid, self.filters, 5)
        with self.assertRaises(QueryResultOverflowError):
            repository.list_category_totals(self.uuid, self.filters)

    def test_cash_flow_points_require_a_positive_width(self) -> None:
        with self.assertRaisesRegex(ValueError, "point_width must be greater than zero"):
            SqliteCashFlowQueryRepository(self.connection).list_points(self.uuid, self.filters, 0)
