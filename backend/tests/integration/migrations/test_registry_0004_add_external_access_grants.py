import unittest
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.migration import SqliteSchemaMigrator
from tests.integration.migrations.fixture import create_database_from_schema_fixture


MIGRATIONS_DIRECTORY = (
    Path(__file__).resolve().parents[3]
    / "app/infrastructure/persistence/sqlite/registry/schema/migrations"
)


class RegistryAddExternalAccessGrantsMigrationTest(unittest.TestCase):
    def test_v4_introduces_shared_grantees_and_preserves_registry_data(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "registry.sqlite"
            create_database_from_schema_fixture("registry_v3.sql", path)

            user_uuid = uuid4()
            ledger_uuid = uuid4()
            grant_uuid = uuid4()
            mfa_uuid = uuid4()
            recovery_uuid = uuid4()
            auth_session_uuid = uuid4()
            remember_session_uuid = uuid4()
            connection = sqlite3.connect(path)
            try:
                connection.execute("PRAGMA foreign_keys = ON")
                connection.execute("INSERT INTO registry_metadata VALUES (1, 3)")
                connection.execute(
                    "INSERT INTO user_account VALUES (?, 'Alice', 'alice', '$argon2id$test', 10, 10)",
                    (user_uuid.bytes,),
                )
                connection.execute(
                    "INSERT INTO ledger VALUES (?, 'Main', 'main.sqlite', 'lucide:BookOpen', ?, 10)",
                    (ledger_uuid.bytes, b"\x80\x80\x80"),
                )
                connection.execute(
                    "INSERT INTO ledger_grant VALUES (?, ?, ?, 'OWNER', 20, NULL)",
                    (grant_uuid.bytes, user_uuid.bytes, ledger_uuid.bytes),
                )
                connection.execute(
                    "INSERT INTO mfa_method VALUES (?, ?, 'TOTP', ?, 30, 630, 31, 1)",
                    (mfa_uuid.bytes, user_uuid.bytes, b"encrypted"),
                )
                connection.execute(
                    "INSERT INTO recovery_code VALUES (?, ?, ?, 30, 60, 40)",
                    (recovery_uuid.bytes, user_uuid.bytes, b"c" * 32),
                )
                connection.execute(
                    "INSERT INTO user_preferences VALUES (?, 'pt-BR', 'DARK')",
                    (user_uuid.bytes,),
                )
                connection.execute(
                    "INSERT INTO auth_session VALUES (?, ?, ?, 30, 90, 10, 35)",
                    (auth_session_uuid.bytes, user_uuid.bytes, b"s" * 32),
                )
                connection.execute(
                    "INSERT INTO remember_session VALUES (?, ?, ?, 30, 90, 35)",
                    (remember_session_uuid.bytes, user_uuid.bytes, b"r" * 32),
                )
                connection.commit()
            finally:
                connection.close()

            migrator = SqliteSchemaMigrator("registry_metadata", 4, MIGRATIONS_DIRECTORY)
            self.assertEqual(migrator.migrate(SqliteDatabase(path)), 1)

            connection = sqlite3.connect(path)
            try:
                grantee = connection.execute("SELECT uuid FROM ledger_grantee").fetchone()
                grant = connection.execute(
                    "SELECT uuid, grantee_uuid, ledger_uuid, role, created_at, revoked_at FROM ledger_grant"
                ).fetchone()
                user = connection.execute(
                    "SELECT uuid, name, normalized_name, password_hash, created_at, password_changed_at FROM user_account"
                ).fetchone()
                preserved_counts = {
                    table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                    for table in (
                        "mfa_method",
                        "recovery_code",
                        "user_preferences",
                        "auth_session",
                        "remember_session",
                    )
                }
                user_foreign_keys = connection.execute("PRAGMA foreign_key_list(user_account)").fetchall()
                external_foreign_keys = connection.execute("PRAGMA foreign_key_list(external_access)").fetchall()
                indexes = {
                    row[0]: row[1]
                    for row in connection.execute(
                        "SELECT name, sql FROM sqlite_schema WHERE type = 'index' AND tbl_name = 'ledger_grant'"
                    )
                    if row[1] is not None
                }
                version = connection.execute(
                    "SELECT schema_version FROM registry_metadata WHERE singleton = 1"
                ).fetchone()[0]
                foreign_key_violations = connection.execute("PRAGMA foreign_key_check").fetchall()
            finally:
                connection.close()

            self.assertEqual(tuple(grantee), (user_uuid.bytes,))
            self.assertEqual(
                tuple(user),
                (user_uuid.bytes, "Alice", "alice", "$argon2id$test", 10, 10),
            )
            self.assertEqual(
                tuple(grant),
                (grant_uuid.bytes, user_uuid.bytes, ledger_uuid.bytes, "OWNER", 20, None),
            )
            self.assertEqual(set(preserved_counts.values()), {1})
            self.assertTrue(any(row[2] == "ledger_grantee" and row[3] == "uuid" and row[4] == "uuid" for row in user_foreign_keys))
            self.assertTrue(any(row[2] == "ledger_grantee" and row[3] == "uuid" and row[4] == "uuid" for row in external_foreign_keys))
            self.assertNotIn("ledger_grant_active_user_ledger_idx", indexes)
            self.assertIn("ledger_grant_active_ledger_owner_idx", indexes)
            self.assertEqual(version, 4)
            self.assertEqual(foreign_key_violations, [])
