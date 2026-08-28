"""Integration tests for indexes declared by the ledger SQLite schema."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.infrastructure.persistence.sqlite.database import SqliteDatabase


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class SqliteLedgerIndexesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "ledger.sqlite"
        self.connection = SqliteDatabase(database_path).get_connection()
        self.connection.executescript(SCHEMA_PATH.read_text())

    def tearDown(self) -> None:
        self.connection.close()
        self.temporary_directory.cleanup()

    def test_defines_indexes_for_event_filters_and_balance_queries(self) -> None:
        """The schema includes every index required by the initial query paths."""
        expected_indexes = {
            "category_name_idx",
            "transaction_event_occurred_at_idx",
            "transaction_tag_tag_event_idx",
            "financial_movement_transaction_event_idx",
            "financial_movement_account_event_idx",
            "financial_movement_category_event_idx",
        }
        rows = self.connection.execute(
            "SELECT name FROM sqlite_schema WHERE type = 'index' AND name NOT LIKE 'sqlite_autoindex_%'"
        ).fetchall()

        self.assertEqual({row["name"] for row in rows}, expected_indexes)

    def test_category_movement_lookup_uses_its_composite_index(self) -> None:
        """SQLite can seek category movements without scanning the complete table."""
        rows = self.connection.execute(
            """
            EXPLAIN QUERY PLAN
            SELECT uuid
            FROM financial_movement
            WHERE category_uuid = ? AND transaction_event_uuid = ?
            """,
            ("category-uuid", "event-uuid"),
        ).fetchall()
        details = " ".join(row["detail"] for row in rows)

        self.assertIn("financial_movement_category_event_idx", details)


if __name__ == "__main__":
    unittest.main()
