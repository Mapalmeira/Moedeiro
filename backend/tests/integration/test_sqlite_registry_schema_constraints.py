"""Integration tests for constraints enforced by the registry SQLite schema."""

import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from app.infrastructure.persistence.sqlite.database import SqliteDatabase


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"


class SqliteRegistrySchemaConstraintsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "registry.sqlite"
        self.connection = SqliteDatabase(database_path).get_connection()
        self.connection.executescript(SCHEMA_PATH.read_text())
        self.ledger_uuid = uuid4().bytes
        self.token_uuid = uuid4().bytes
        self.connection.execute(
            "INSERT INTO ledger VALUES (?, 'ledger.sqlite')",
            (self.ledger_uuid,),
        )
        self.connection.execute(
            "INSERT INTO ledger_token VALUES (?, ?, 'token-hash', 'personal', 0, NULL)",
            (self.token_uuid, self.ledger_uuid),
        )

    def tearDown(self) -> None:
        self.connection.close()
        self.temporary_directory.cleanup()

    def test_declares_and_stores_uuid_as_16_byte_blob(self) -> None:
        ledger_columns = {row["name"]: row["type"] for row in self.connection.execute("PRAGMA table_info(ledger)")}
        token_columns = {row["name"]: row["type"] for row in self.connection.execute("PRAGMA table_info(ledger_token)")}
        row = self.connection.execute(
            "SELECT typeof(uuid) AS storage_type, length(uuid) AS size FROM ledger"
        ).fetchone()

        self.assertEqual(ledger_columns["uuid"], "BLOB")
        self.assertEqual(token_columns["uuid"], "BLOB")
        self.assertEqual(token_columns["ledger_uuid"], "BLOB")
        self.assertEqual(row["storage_type"], "blob")
        self.assertEqual(row["size"], 16)

    def test_rejects_uuid_with_invalid_size(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                "INSERT INTO ledger VALUES (?, 'other.sqlite')",
                (b"invalid",),
            )

    def test_enforces_domain_text_lengths(self) -> None:
        invalid_values = (
            ("ledger", "path", ""),
            ("ledger_token", "token_hash", ""),
            ("ledger_token", "token_hash", "x" * 256),
            ("ledger_token", "label", "x" * 31),
        )

        for table, column, value in invalid_values:
            with self.subTest(table=table, column=column, size=len(value)):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.connection.execute(f"UPDATE {table} SET {column} = ?", (value,))


if __name__ == "__main__":
    unittest.main()
