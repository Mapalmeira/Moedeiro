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
        self.connection = SqliteDatabase(Path(self.temporary_directory.name) / "registry.sqlite").get_connection()
        self.connection.executescript(SCHEMA_PATH.read_text())
        self.ledger_uuid = uuid4().bytes
        self.invitation_uuid = uuid4().bytes
        self.grant_uuid = uuid4().bytes
        self.session_uuid = uuid4().bytes
        self.connection.execute("INSERT INTO ledger VALUES (?, 'ledger.sqlite')", (self.ledger_uuid,))
        self.connection.execute("INSERT INTO access_invitation VALUES (?, ?, ?, ?, 10, 90, NULL, NULL)", (self.invitation_uuid, self.ledger_uuid, self.grant_uuid, b"i" * 32))
        self.connection.execute("INSERT INTO access_grant VALUES (?, ?, 'WEBCRYPTO', 'browser', ?, 'ES256', NULL, NULL, 20, NULL)", (self.grant_uuid, self.ledger_uuid, b"public-key"))
        self.connection.execute("INSERT INTO auth_session VALUES (?, ?, ?, 40, 1800, 43200, NULL, NULL)", (self.session_uuid, self.grant_uuid, b"s" * 32))

    def tearDown(self) -> None:
        self.connection.close()
        self.temporary_directory.cleanup()

    def test_declares_every_uuid_column_as_blob(self) -> None:
        """Entity identities and all UUID foreign keys use the same binary representation."""
        expected_columns = {
            "ledger": {"uuid"},
            "access_invitation": {"uuid", "ledger_uuid", "grant_uuid"},
            "access_grant": {"uuid", "ledger_uuid"},
            "auth_session": {"uuid", "grant_uuid"},
        }
        for table, uuid_columns in expected_columns.items():
            columns = {row["name"]: row["type"] for row in self.connection.execute(f"PRAGMA table_info({table})")}
            with self.subTest(table=table):
                self.assertEqual({column: columns[column] for column in uuid_columns}, {column: "BLOB" for column in uuid_columns})

    def test_stores_uuid_as_exactly_16_bytes(self) -> None:
        """SQLite stores the binary UUID value without textual conversion."""
        row = self.connection.execute("SELECT typeof(uuid) AS storage_type, length(uuid) AS size FROM ledger").fetchone()

        self.assertEqual(row["storage_type"], "blob")
        self.assertEqual(row["size"], 16)

    def test_rejects_uuid_with_invalid_size(self) -> None:
        """The schema rejects a BLOB that is not a complete UUID."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("INSERT INTO ledger VALUES (?, 'other.sqlite')", (b"invalid",))

    def test_enforces_invitation_and_session_hash_sizes(self) -> None:
        """Persisted digests must match the selected 256-bit hash output."""
        invalid_updates = (
            ("access_invitation", "secret_hash", b"x" * 31),
            ("auth_session", "token_hash", b"x" * 31),
        )
        for table, column, value in invalid_updates:
            with self.subTest(table=table, column=column):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.connection.execute(f"UPDATE {table} SET {column} = ?", (value,))

    def test_enforces_grant_field_limits(self) -> None:
        """The combined authorization and credential record uses domain limits."""
        invalid_updates = (("label", "x" * 31), ("public_key", b""), ("public_key", b"x" * 4097))
        for column, value in invalid_updates:
            with self.subTest(column=column, size=len(value)):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.connection.execute(f"UPDATE access_grant SET {column} = ?", (value,))

    def test_enforces_authentication_method_specific_state(self) -> None:
        """A WebCrypto grant cannot contain authenticator-only state."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("UPDATE access_grant SET credential_id = ?, signature_counter = 0", (b"credential-id",))

    def test_enforces_session_timeout_limits(self) -> None:
        invalid_updates = (("inactivity_timeout_seconds", 0), ("absolute_timeout_seconds", 0), ("inactivity_timeout_seconds", 43201))
        for column, value in invalid_updates:
            with self.subTest(column=column, value=value):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.connection.execute(f"UPDATE auth_session SET {column} = ?", (value,))

    def test_enforces_invitation_expiration_timeout(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("UPDATE access_invitation SET expiration_timeout_seconds = 0")

    def test_consumption_and_usage_must_precede_expiration(self) -> None:
        """Expired invitations and sessions cannot record a successful use."""
        invalid_updates = (
            ("access_invitation", "consumed_at", 100),
            ("auth_session", "last_activity_at", 43240),
        )
        for table, column, timestamp in invalid_updates:
            with self.subTest(table=table, column=column):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.connection.execute(f"UPDATE {table} SET {column} = ?", (timestamp,))

    def test_grant_survives_removal_of_its_consumed_invitation(self) -> None:
        """The temporary invitation does not own the lifetime of the resulting grant."""
        self.connection.execute("UPDATE access_invitation SET consumed_at = 30 WHERE uuid = ?", (self.invitation_uuid,))
        self.connection.execute("DELETE FROM access_invitation WHERE uuid = ?", (self.invitation_uuid,))

        row = self.connection.execute("SELECT uuid FROM access_grant WHERE uuid = ?", (self.grant_uuid,)).fetchone()

        self.assertIsNotNone(row)


if __name__ == "__main__":
    unittest.main()
