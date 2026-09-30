import sqlite3
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from app.application.ledger.exceptions import QueryResultOverflowError
from app.domain.ledger.model.financial_event_filter import FinancialEventFilter
from app.infrastructure.persistence.sqlite.ledger.repository.cash_flow_query import SqliteCashFlowQueryRepository


class CashFlowQueryRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = MagicMock()
        self.connection.execute.side_effect = sqlite3.OperationalError("integer overflow")
        self.repository = SqliteCashFlowQueryRepository(self.connection)
        self.currency_uuid = uuid4()
        self.filters = FinancialEventFilter(from_timestamp=0, to_timestamp=10)

    def test_queries_translate_integer_overflow(self) -> None:
        with self.assertRaises(QueryResultOverflowError):
            self.repository.get_summary(self.currency_uuid, self.filters)
        with self.assertRaises(QueryResultOverflowError):
            self.repository.list_points(self.currency_uuid, self.filters, 5)
        with self.assertRaises(QueryResultOverflowError):
            self.repository.list_category_totals(self.currency_uuid, self.filters)

    def test_points_require_a_positive_width(self) -> None:
        with self.assertRaisesRegex(ValueError, "point_width must be greater than zero"):
            self.repository.list_points(self.currency_uuid, self.filters, 0)
