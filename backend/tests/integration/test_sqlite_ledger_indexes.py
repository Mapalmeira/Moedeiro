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
            "category_parent_idx",
            "financial_event_occurred_at_idx",
            "financial_event_type_occurred_at_idx",
            "financial_movement_financial_event_idx",
            "financial_movement_account_event_idx",
            "financial_movement_category_event_idx",
            "account_currency_idx",
            "budget_to_from_idx",
            "budget_accounts_account_idx",
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
            WHERE category_uuid = ? AND financial_event_uuid = ?
            """,
            ("category-uuid", "event-uuid"),
        ).fetchall()
        details = " ".join(row["detail"] for row in rows)

        self.assertIn("financial_movement_category_event_idx", details)

    def test_descendant_category_lookup_uses_parent_index(self) -> None:
        rows = self.connection.execute(
            "EXPLAIN QUERY PLAN SELECT uuid FROM category WHERE parent_uuid = ?",
            ("category-uuid",),
        ).fetchall()
        details = " ".join(row["detail"] for row in rows)

        self.assertIn("category_parent_idx", details)

    def test_event_type_and_period_filter_uses_composite_index(self) -> None:
        rows = self.connection.execute(
            "EXPLAIN QUERY PLAN SELECT uuid FROM financial_event WHERE type = ? AND occurred_at >= ? AND occurred_at < ? ORDER BY occurred_at, uuid",
            ("TRANSACTION", 10, 20),
        ).fetchall()
        details = " ".join(row["detail"] for row in rows)

        self.assertIn("financial_event_type_occurred_at_idx", details)
        self.assertNotIn("USE TEMP B-TREE FOR ORDER BY", details)

    def test_event_category_filter_uses_both_columns_of_a_composite_index(self) -> None:
        rows = self.connection.execute(
            "EXPLAIN QUERY PLAN SELECT uuid FROM financial_movement WHERE financial_event_uuid = ? AND category_uuid = ?",
            (b"event", b"category"),
        ).fetchall()
        details = " ".join(row["detail"] for row in rows)

        self.assertTrue(
            "financial_movement_financial_event_idx" in details
            or "financial_movement_category_event_idx" in details
        )
        self.assertIn("financial_event_uuid=?", details)
        self.assertIn("category_uuid=?", details)

    def test_category_order_uses_index_without_temporary_sort(self) -> None:
        rows = self.connection.execute(
            "EXPLAIN QUERY PLAN SELECT uuid FROM category ORDER BY category_name, uuid"
        ).fetchall()
        details = " ".join(row["detail"] for row in rows)

        self.assertIn("category_name_idx", details)
        self.assertNotIn("USE TEMP B-TREE FOR ORDER BY", details)

    def test_budget_period_and_currency_queries_use_declared_indexes(self) -> None:
        queries = (
            ("SELECT uuid FROM budget WHERE from_timestamp <= ? AND to_timestamp > ?", (10, 10), "budget_to_from_idx"),
            ("SELECT uuid FROM account WHERE currency_uuid = ?", (b"currency",), "account_currency_idx"),
            ("SELECT budget_uuid FROM budget_accounts WHERE account_uuid = ?", (b"account",), "budget_accounts_account_idx"),
        )
        for query, parameters, index_name in queries:
            with self.subTest(index_name=index_name):
                rows = self.connection.execute(f"EXPLAIN QUERY PLAN {query}", parameters).fetchall()
                details = " ".join(row["detail"] for row in rows)

                self.assertIn(index_name, details)


if __name__ == "__main__":
    unittest.main()
