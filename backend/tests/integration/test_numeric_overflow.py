import sqlite3
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.application.ledger.exceptions import QueryResultOverflowError
from app.factory import _add_numeric_error_handlers
from app.infrastructure.persistence.sqlite.ledger.repository._numeric import require_sqlite_integer


class NumericOverflowTest(unittest.TestCase):
    def test_sqlite_integer_input_and_aggregate_overflows_return_422(self) -> None:
        application = FastAPI()
        _add_numeric_error_handlers(application)

        @application.get("/input")
        def overflow_input() -> None:
            sqlite3.connect(":memory:").execute("SELECT ?", ((1 << 63),))

        @application.get("/aggregate")
        def overflow_aggregate() -> None:
            connection = sqlite3.connect(":memory:")
            try:
                connection.executescript("CREATE TABLE number(value INTEGER); INSERT INTO number VALUES (9223372036854775807), (1);")
                try:
                    connection.execute("SELECT SUM(value) FROM number").fetchone()
                except sqlite3.OperationalError as error:
                    if str(error) == "integer overflow":
                        raise QueryResultOverflowError from error
                    raise
            finally:
                connection.close()

        with TestClient(application) as client:
            for path, detail in (
                ("/input", "Integer must fit signed 64-bit range"),
                ("/aggregate", "Query result exceeds signed 64-bit range"),
            ):
                response = client.get(path)
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json(), {"detail": detail})

    def test_sqlite_real_result_from_an_overflowing_product_is_rejected(self) -> None:
        value = sqlite3.connect(":memory:").execute("SELECT 9223372036854775807 * 2").fetchone()[0]

        self.assertIsInstance(value, float)
        with self.assertRaises(QueryResultOverflowError):
            require_sqlite_integer(value)


if __name__ == "__main__":
    unittest.main()
