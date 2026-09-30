import sqlite3
import unittest

from app.application.ledger.exceptions import QueryResultOverflowError
from app.infrastructure.persistence.sqlite.ledger.repository._numeric import raise_query_result_overflow, require_sqlite_integer


class NumericTest(unittest.TestCase):
    def test_sqlite_real_result_from_an_overflowing_product_is_rejected(self) -> None:
        connection = sqlite3.connect(":memory:")
        try:
            value = connection.execute("SELECT 9223372036854775807 * 2").fetchone()[0]
        finally:
            connection.close()

        self.assertIsInstance(value, float)
        with self.assertRaises(QueryResultOverflowError):
            require_sqlite_integer(value)

    def test_translates_only_sqlite_integer_overflow(self) -> None:
        overflow = sqlite3.OperationalError("integer overflow")
        with self.assertRaises(QueryResultOverflowError) as raised:
            raise_query_result_overflow(overflow)
        self.assertIs(raised.exception.__cause__, overflow)

        other_error = sqlite3.OperationalError("database is locked")
        with self.assertRaises(sqlite3.OperationalError) as raised:
            raise_query_result_overflow(other_error)
        self.assertIs(raised.exception, other_error)
