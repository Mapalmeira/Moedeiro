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

    def test_defines_only_indexes_used_by_registry_queries(self) -> None:
        expected_indexes = {
            "ledger_grant_active_user_ledger_idx",
            "ledger_grant_active_ledger_owner_idx",
            "ledger_grant_user_idx",
            "ledger_grant_ledger_idx",
            "ledger_grant_revoked_idx",
            "recovery_code_user_idx",
            "recovery_code_active_user_idx",
            "recovery_code_used_idx",
            "recovery_code_expires_idx",
            "auth_session_user_idx",
            "auth_session_expires_idx",
            "auth_session_inactive_idx",
            "remember_session_user_idx",
            "remember_session_expires_idx",
            "user_invitation_consumed_idx",
            "user_invitation_expires_idx",
            "mfa_method_unconfirmed_idx",
        }
        rows = self.connection.execute("SELECT name FROM sqlite_schema WHERE type = 'index' AND name NOT LIKE 'sqlite_autoindex_%'").fetchall()

        self.assertEqual({row["name"] for row in rows}, expected_indexes)

    def test_repository_queries_use_declared_indexes(self) -> None:
        queries = (
            (
                "SELECT uuid FROM ledger_grant WHERE user_uuid = ? AND ledger_uuid = ? AND revoked_at IS NULL",
                (b"user", b"ledger"),
                "ledger_grant_active_user_ledger_idx",
            ),
            ("SELECT uuid FROM ledger_grant WHERE user_uuid = ?", (b"user",), "ledger_grant_user_idx"),
            ("SELECT uuid FROM ledger_grant WHERE ledger_uuid = ?", (b"ledger",), "ledger_grant_ledger_idx"),
            ("SELECT uuid FROM recovery_code WHERE user_uuid = ?", (b"user",), "recovery_code_user_idx"),
            ("SELECT uuid FROM recovery_code WHERE user_uuid = ? AND used_at IS NULL", (b"user",), "recovery_code_active_user_idx"),
            ("SELECT uuid FROM auth_session WHERE user_uuid = ?", (b"user",), "auth_session_user_idx"),
            ("SELECT uuid FROM remember_session WHERE user_uuid = ?", (b"user",), "remember_session_user_idx"),
            ("DELETE FROM ledger_grant WHERE revoked_at <= ?", (100,), "ledger_grant_revoked_idx"),
            ("DELETE FROM user_invitation WHERE consumed_at <= ?", (100,), "user_invitation_consumed_idx"),
            ("DELETE FROM user_invitation WHERE expires_at <= ?", (100,), "user_invitation_expires_idx"),
            ("DELETE FROM recovery_code WHERE used_at <= ?", (100,), "recovery_code_used_idx"),
            ("DELETE FROM recovery_code WHERE expires_at <= ?", (100,), "recovery_code_expires_idx"),
            ("DELETE FROM auth_session WHERE expires_at <= ?", (100,), "auth_session_expires_idx"),
            ("DELETE FROM auth_session WHERE COALESCE(last_activity_at, created_at) + inactivity_timeout_seconds <= ?", (100,), "auth_session_inactive_idx"),
            ("DELETE FROM remember_session WHERE expires_at <= ?", (100,), "remember_session_expires_idx"),
            ("DELETE FROM mfa_method WHERE confirmed_at IS NULL AND created_at <= ?", (100,), "mfa_method_unconfirmed_idx"),
        )
        for query, parameters, index_name in queries:
            with self.subTest(index_name=index_name):
                rows = self.connection.execute(f"EXPLAIN QUERY PLAN {query}", parameters).fetchall()
                details = " ".join(row["detail"] for row in rows)

                self.assertIn(index_name, details)

    def test_totp_uniqueness_index_also_supports_user_lookup(self) -> None:
        rows = self.connection.execute("EXPLAIN QUERY PLAN SELECT uuid FROM mfa_method WHERE user_uuid = ?", (b"user",)).fetchall()
        details = " ".join(row["detail"] for row in rows)

        self.assertIn("sqlite_autoindex_mfa_method_", details)


if __name__ == "__main__":
    unittest.main()
