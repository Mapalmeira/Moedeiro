"""Integration tests for indexes declared by the registry SQLite schema."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.infrastructure.persistence.sqlite.database import SqliteDatabase


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"


class SqliteRegistryIndexesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.connection = SqliteDatabase(Path(self.temporary_directory.name) / "registry.sqlite").get_connection()
        self.connection.executescript(SCHEMA_PATH.read_text())

    def tearDown(self) -> None:
        self.connection.close()
        self.temporary_directory.cleanup()

    def test_defines_indexes_for_lookup_listing_and_expiration(self) -> None:
        """The schema contains all explicitly named registry query indexes."""
        expected_indexes = {
            "access_invitation_ledger_idx",
            "access_invitation_created_at_idx",
            "access_grant_ledger_idx",
            "access_grant_credential_id_idx",
            "auth_session_grant_idx",
            "auth_session_created_at_idx",
            "auth_session_last_activity_at_idx",
        }
        rows = self.connection.execute("SELECT name FROM sqlite_schema WHERE type = 'index' AND name NOT LIKE 'sqlite_autoindex_%'").fetchall()

        self.assertEqual({row["name"] for row in rows}, expected_indexes)

    def test_session_cleanup_uses_activity_indexes(self) -> None:
        """Session age and last activity can be filtered without full table scans."""
        queries = (
            ("SELECT uuid FROM auth_session WHERE created_at <= ?", "auth_session_created_at_idx"),
            ("SELECT uuid FROM auth_session WHERE last_activity_at <= ?", "auth_session_last_activity_at_idx"),
        )
        for query, index_name in queries:
            with self.subTest(index_name=index_name):
                rows = self.connection.execute(f"EXPLAIN QUERY PLAN {query}", (100,)).fetchall()
                details = " ".join(row["detail"] for row in rows)

                self.assertIn(index_name, details)


if __name__ == "__main__":
    unittest.main()
