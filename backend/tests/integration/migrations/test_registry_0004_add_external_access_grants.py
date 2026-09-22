from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.migration import SqliteSchemaMigrator
from tests.integration.migrations.fixture import create_database_from_schema_fixture


MIGRATIONS_DIRECTORY = (
    Path(__file__).resolve().parents[3]
    / "app/infrastructure/persistence/sqlite/registry/schema/migrations"
)


class RegistryAddExternalAccessGrantsMigrationTest(unittest.TestCase):
    def test_v4_replaces_role_with_type_and_adds_token_grants(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "registry.sqlite"
            create_database_from_schema_fixture("registry_v3.sql", path)

            user_uuid = uuid4()
            ledger_uuid = uuid4()
            grant_uuid = uuid4()
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
                connection.commit()
            finally:
                connection.close()

            migrator = SqliteSchemaMigrator("registry_metadata", 4, MIGRATIONS_DIRECTORY)
            self.assertEqual(migrator.migrate(SqliteDatabase(path)), 1)

            connection = sqlite3.connect(path)
            try:
                grant = connection.execute(
                    "SELECT uuid, user_uuid, ledger_uuid, type, created_at, revoked_at FROM ledger_grant"
                ).fetchone()
                token_table = connection.execute(
                    "SELECT name FROM sqlite_schema WHERE type = 'table' AND name = 'ledger_token_grant'"
                ).fetchone()
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

            self.assertEqual(
                tuple(grant),
                (grant_uuid.bytes, user_uuid.bytes, ledger_uuid.bytes, "OWNER", 20, None),
            )
            self.assertIsNotNone(token_table)
            self.assertNotIn("ledger_grant_active_user_ledger_idx", indexes)
            self.assertIn("ledger_grant_active_ledger_owner_idx", indexes)
            self.assertEqual(version, 4)
            self.assertEqual(foreign_key_violations, [])


if __name__ == "__main__":
    unittest.main()
