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
            "user_invitation_expires_at_idx",
            "ledger_grant_active_user_ledger_idx",
            "ledger_grant_user_idx",
            "ledger_grant_ledger_idx",
            "webauthn_credential_user_idx",
            "mfa_method_user_idx",
            "recovery_code_user_idx",
            "auth_session_user_idx",
            "auth_session_expires_at_idx",
            "auth_session_inactivity_expiration_idx",
            "remember_session_user_idx",
            "remember_session_expires_at_idx",
        }
        rows = self.connection.execute("SELECT name FROM sqlite_schema WHERE type = 'index' AND name NOT LIKE 'sqlite_autoindex_%'").fetchall()

        self.assertEqual({row["name"] for row in rows}, expected_indexes)

    def test_session_cleanup_uses_time_indexes(self) -> None:
        """Expired sessions can be filtered without full table scans."""
        queries = (
            ("SELECT uuid FROM user_invitation WHERE expires_at <= ?", "user_invitation_expires_at_idx"),
            ("SELECT uuid FROM auth_session WHERE expires_at <= ?", "auth_session_expires_at_idx"),
            ("SELECT uuid FROM auth_session WHERE COALESCE(last_activity_at, created_at) + inactivity_timeout_seconds <= ?", "auth_session_inactivity_expiration_idx"),
            ("SELECT uuid FROM remember_session WHERE expires_at <= ?", "remember_session_expires_at_idx"),
        )
        for query, index_name in queries:
            with self.subTest(index_name=index_name):
                rows = self.connection.execute(f"EXPLAIN QUERY PLAN {query}", (100,)).fetchall()
                details = " ".join(row["detail"] for row in rows)

                self.assertIn(index_name, details)


if __name__ == "__main__":
    unittest.main()
