import sqlite3
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from app.application.ledger.exceptions import QueryResultOverflowError
from app.infrastructure.persistence.sqlite.ledger.repository.account_balance_query import SqliteAccountBalanceQueryRepository


class AccountBalanceQueryErrorsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = MagicMock()
        self.repository = SqliteAccountBalanceQueryRepository(self.connection)
        self.uuid = uuid4()

    def test_balance_queries_translate_sqlite_integer_overflow(self) -> None:
        existing = MagicMock()
        existing.fetchone.return_value = (1,)
        self.connection.execute.side_effect = [existing, sqlite3.OperationalError("integer overflow")]
        with self.assertRaises(QueryResultOverflowError):
            self.repository.get_balance_at(self.uuid, 10)

        self.connection.execute.side_effect = sqlite3.OperationalError("integer overflow")
        with self.assertRaises(QueryResultOverflowError):
            self.repository.get_currency_balance_at(self.uuid, 10)

    def test_balance_list_rejects_invalid_limit_and_translates_overflow(self) -> None:
        with self.assertRaisesRegex(ValueError, "limit must be greater than zero"):
            self.repository.list_balances_at(10, limit=0)

        self.connection.execute.side_effect = sqlite3.OperationalError("integer overflow")
        with self.assertRaises(QueryResultOverflowError):
            self.repository.list_balances_at(10)

    def test_point_query_translates_sqlite_integer_overflow(self) -> None:
        existing = MagicMock()
        existing.fetchone.return_value = (1,)
        self.connection.execute.side_effect = [existing, sqlite3.OperationalError("integer overflow")]

        with self.assertRaises(QueryResultOverflowError):
            self.repository.list_points(self.uuid, 10, 2, 5)
