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
        self.movement_uuid = uuid4().bytes
        self.budget_uuid = uuid4().bytes
        self.connection.execute(
            "INSERT INTO ledger_metadata VALUES (1, ?, 1, 0)",
            (self.ledger_uuid,),
        )
        self.connection.execute(
            "INSERT INTO currency VALUES (?, 'Real', NULL, 'R$', 2, 'unicode:R$', ?)",
            (self.currency_uuid, b"\x80\x80\x80"),
        )
        self.connection.execute(
            "INSERT INTO account VALUES (?, 'Checking', NULL, ?, 'lucide:WalletCards', ?)",
            (self.account_uuid, self.currency_uuid, b"\x80\x80\x80"),
        )
        self.connection.execute(
            "INSERT INTO category VALUES (?, 'Food', 'lucide:Utensils', ?, NULL)",
            (self.category_uuid, b"\xff\x80\x00"),
        )
        self.connection.execute(
            "INSERT INTO financial_event VALUES (?, 0, 'Purchase', 'TRANSACTION')",
            (self.event_uuid,),
        )
        self.connection.execute(
            "INSERT INTO financial_movement VALUES (?, ?, -100, 1, 'Lunch', ?, ?)",
            (self.movement_uuid, self.event_uuid, self.account_uuid, self.category_uuid),
        )
        self.connection.execute(
            "INSERT INTO budget VALUES (?, 0, 10, 'Monthly', 'Spending', 100, ?, ?)",
            (self.budget_uuid, self.account_uuid, self.category_uuid),
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
            "financial_event": {"uuid"},
            "financial_movement": {"uuid", "financial_event_uuid", "account_uuid", "category_uuid"},
            "budget": {"uuid", "account_uuid", "category_uuid"},
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

    def test_currency_names_are_unique(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                "INSERT INTO currency VALUES (?, 'Real', NULL, NULL, 2, 'unicode:$', ?)",
                (uuid4().bytes, b"\x80\x80\x80"),
            )

    def test_category_names_are_unique(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                "INSERT INTO category VALUES (?, 'Food', 'lucide:Circle', ?, NULL)",
                (uuid4().bytes, b"\x80\x80\x80"),
            )

    def test_schema_has_no_collection_size_triggers(self) -> None:
        triggers = self.connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger' ORDER BY name"
        ).fetchall()

        self.assertEqual(triggers, [])

    def test_enforces_ledger_metadata_schema_version_and_creation_timestamp(self) -> None:
        for column, value in (("schema_version", 0), ("created_at", -1)):
            with self.subTest(column=column):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.connection.execute(f"UPDATE ledger_metadata SET {column} = ?", (value,))

    def test_enforces_domain_text_lengths(self) -> None:
        invalid_values = (
            ("currency", "currency_name", ""),
            ("currency", "currency_name", "x" * 31),
            ("currency", "prefix", "x" * 11),
            ("currency", "suffix", "x" * 11),
            ("account", "account_name", ""),
            ("account", "account_name", "x" * 51),
            ("account", "note", "x" * 301),
            ("category", "category_name", ""),
            ("category", "category_name", "x" * 31),
            ("financial_event", "description", ""),
            ("financial_event", "description", "x" * 301),
            ("financial_movement", "item_name", "x" * 51),
            ("budget", "budget_name", ""),
            ("budget", "budget_name", "x" * 51),
            ("budget", "description", ""),
            ("budget", "description", "x" * 301),
        )

        for table, column, value in invalid_values:
            with self.subTest(table=table, column=column, size=len(value)):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.connection.execute(f"UPDATE {table} SET {column} = ?", (value,))

    def test_icon_columns_enforce_only_the_one_to_one_hundred_character_length(self) -> None:
        for table in ("currency", "account", "category"):
            for value in ("x", "x" * 100, "not-a-domain-icon", "unicode:ABCD"):
                with self.subTest(table=table, value=value):
                    self.connection.execute(f"UPDATE {table} SET icon = ?", (value,))
                    stored = self.connection.execute(f"SELECT icon FROM {table}").fetchone()[0]
                    self.assertEqual(stored, value)

            for value in ("", "x" * 101):
                with self.subTest(table=table, size=len(value)):
                    with self.assertRaises(sqlite3.IntegrityError):
                        self.connection.execute(f"UPDATE {table} SET icon = ?", (value,))

    def test_enforces_color_as_rgb_bytes(self) -> None:
        for table in ("currency", "account", "category"):
            for color_code in (b"\x00\x00", b"\x00" * 4):
                with self.subTest(table=table, size=len(color_code)):
                    with self.assertRaises(sqlite3.IntegrityError):
                        self.connection.execute(f"UPDATE {table} SET color_code = ?", (color_code,))

    def test_enforces_positive_financial_movement_quantity(self) -> None:
        for quantity in (0, -1):
            with self.subTest(quantity=quantity):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.connection.execute("UPDATE financial_movement SET quantity = ?", (quantity,))

if __name__ == "__main__":
    unittest.main()
