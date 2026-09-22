from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.migration import SqliteSchemaMigrator


MIGRATIONS_DIRECTORY = (
    Path(__file__).resolve().parents[3]
    / "app/infrastructure/persistence/sqlite/registry/schema/migrations"
)


class RegistryAddExternalAccessGrantsMigrationTest(unittest.TestCase):
    def test_v4_replaces_role_with_type_and_adds_token_grants(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "registry.sqlite"
            user_uuid = uuid4()
            ledger_uuid = uuid4()
            grant_uuid = uuid4()
            connection = sqlite3.connect(path)
            try:
                connection.executescript(
                    """
                    CREATE TABLE registry_metadata (
                        singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                        schema_version INTEGER NOT NULL CHECK (schema_version >= 1)
                    ) STRICT;
                    CREATE TABLE user_account (
                        uuid BLOB PRIMARY KEY,
                        name TEXT NOT NULL,
                        normalized_name TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        created_at INTEGER NOT NULL,
                        password_changed_at INTEGER NOT NULL
                    ) STRICT;
                    CREATE TABLE ledger (
                        uuid BLOB PRIMARY KEY,
                        name TEXT NOT NULL,
                        path TEXT NOT NULL UNIQUE,
                        icon TEXT NOT NULL,
                        color_code BLOB NOT NULL,
                        last_accessed_at INTEGER NOT NULL
                    ) STRICT;
                    CREATE TABLE ledger_grant (
                        uuid BLOB PRIMARY KEY,
                        user_uuid BLOB NOT NULL,
                        ledger_uuid BLOB NOT NULL,
                        role TEXT NOT NULL CHECK (role IN ('OWNER')),
                        created_at INTEGER NOT NULL CHECK (created_at >= 0),
                        revoked_at INTEGER CHECK (revoked_at IS NULL OR revoked_at >= created_at),
                        FOREIGN KEY (user_uuid) REFERENCES user_account(uuid) ON DELETE CASCADE,
                        FOREIGN KEY (ledger_uuid) REFERENCES ledger(uuid) ON DELETE CASCADE
                    ) STRICT;
                    CREATE UNIQUE INDEX ledger_grant_active_user_ledger_idx
                    ON ledger_grant(user_uuid, ledger_uuid) WHERE revoked_at IS NULL;
                    CREATE UNIQUE INDEX ledger_grant_active_ledger_owner_idx
                    ON ledger_grant(ledger_uuid) WHERE revoked_at IS NULL AND role = 'OWNER';
                    CREATE INDEX ledger_grant_user_idx ON ledger_grant(user_uuid);
                    CREATE INDEX ledger_grant_ledger_idx ON ledger_grant(ledger_uuid);
                    CREATE INDEX ledger_grant_revoked_idx
                    ON ledger_grant(revoked_at) WHERE revoked_at IS NOT NULL;
                    INSERT INTO registry_metadata(singleton, schema_version) VALUES (1, 3);
                    """
                )
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
                connection.execute("PRAGMA foreign_keys = ON")
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
