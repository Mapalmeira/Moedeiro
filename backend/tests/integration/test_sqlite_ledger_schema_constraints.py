"""Integration tests for constraints enforced by the ledger SQLite schema."""

import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from app.infrastructure.persistence.sqlite.database import SqliteDatabase


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class SqliteLedgerSchemaConstraintsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "ledger.sqlite"
        self.connection = SqliteDatabase(database_path).get_connection()
        self.connection.executescript(SCHEMA_PATH.read_text())
        self.ledger_uuid = uuid4().bytes
        self.currency_uuid = uuid4().bytes
        self.account_uuid = uuid4().bytes
        self.category_uuid = uuid4().bytes
        self.event_uuid = uuid4().bytes
        self.tag_uuid = uuid4().bytes
        self.movement_uuid = uuid4().bytes
        self.budget_uuid = uuid4().bytes
        self.connection.execute(
            "INSERT INTO ledger_metadata VALUES (1, ?, 'Ledger', 1, 0)",
            (self.ledger_uuid,),
        )
        self.connection.execute(
            "INSERT INTO currency VALUES (?, 'Real', NULL, 'R$', 2)",
            (self.currency_uuid,),
        )
        self.connection.execute(
            "INSERT INTO account VALUES (?, 'Checking', NULL, ?)",
            (self.account_uuid, self.currency_uuid),
        )
        self.connection.execute(
            "INSERT INTO category VALUES (?, 'Food', NULL)",
            (self.category_uuid,),
        )
        self.connection.execute(
            "INSERT INTO transaction_event VALUES (?, 0, 'Purchase', 'TRANSACTION')",
            (self.event_uuid,),
        )
        self.connection.execute(
            "INSERT INTO tag VALUES (?, 'Important')",
            (self.tag_uuid,),
        )
        self.connection.execute(
            "INSERT INTO financial_movement VALUES (?, ?, -100, 'Lunch', ?, ?)",
            (self.movement_uuid, self.event_uuid, self.account_uuid, self.category_uuid),
        )
        self.connection.execute(
            "INSERT INTO budget VALUES (?, 0, 10, 'Monthly', 'Spending', 100, ?, ?)",
            (self.budget_uuid, self.category_uuid, self.currency_uuid),
        )

    def tearDown(self) -> None:
        self.connection.close()
        self.temporary_directory.cleanup()

    def test_declares_every_uuid_column_as_blob(self) -> None:
        uuid_columns = {
            "ledger_metadata": {"ledger_uuid"},
            "currency": {"uuid"},
            "account": {"uuid", "currency_uuid"},
            "category": {"uuid", "parent_uuid"},
            "transaction_event": {"uuid"},
            "tag": {"uuid"},
            "transaction_tag": {"transaction_event_uuid", "tag_uuid"},
            "financial_movement": {"uuid", "transaction_event_uuid", "account_uuid", "category_uuid"},
            "budget": {"uuid", "category_uuid", "currency_uuid"},
            "budget_accounts": {"budget_uuid", "account_uuid", "currency_uuid"},
        }

        for table, expected_columns in uuid_columns.items():
            with self.subTest(table=table):
                rows = self.connection.execute(f"PRAGMA table_info({table})").fetchall()
                types = {row["name"]: row["type"] for row in rows}
                self.assertEqual({column: types[column] for column in expected_columns}, dict.fromkeys(expected_columns, "BLOB"))

    def test_stores_uuid_as_exactly_16_bytes(self) -> None:
        row = self.connection.execute(
            "SELECT typeof(uuid) AS storage_type, length(uuid) AS size FROM currency"
        ).fetchone()

        self.assertEqual(row["storage_type"], "blob")
        self.assertEqual(row["size"], 16)

    def test_rejects_uuid_with_invalid_size(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                "INSERT INTO currency VALUES (?, 'Dollar', NULL, '$', 2)",
                (b"invalid",),
            )

    def test_enforces_domain_text_lengths(self) -> None:
        invalid_values = (
            ("ledger_metadata", "name", ""),
            ("ledger_metadata", "name", "x" * 31),
            ("currency", "currency_name", ""),
            ("currency", "currency_name", "x" * 31),
            ("currency", "prefix", "x" * 11),
            ("currency", "suffix", "x" * 11),
            ("account", "account_name", ""),
            ("account", "account_name", "x" * 31),
            ("account", "note", "x" * 301),
            ("category", "category_name", ""),
            ("category", "category_name", "x" * 31),
            ("transaction_event", "description", ""),
            ("transaction_event", "description", "x" * 301),
            ("tag", "name", ""),
            ("tag", "name", "x" * 31),
            ("financial_movement", "item_name", "x" * 31),
            ("budget", "budget_name", ""),
            ("budget", "budget_name", "x" * 31),
            ("budget", "description", ""),
            ("budget", "description", "x" * 301),
        )

        for table, column, value in invalid_values:
            with self.subTest(table=table, column=column, size=len(value)):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.connection.execute(f"UPDATE {table} SET {column} = ?", (value,))


if __name__ == "__main__":
    unittest.main()
