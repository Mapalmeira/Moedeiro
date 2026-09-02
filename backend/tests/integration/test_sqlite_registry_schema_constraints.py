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
        self.invitation_uuid = uuid4().bytes
        self.user_uuid = uuid4().bytes
        self.ledger_uuid = uuid4().bytes
        self.grant_uuid = uuid4().bytes
        self.auth_session_uuid = uuid4().bytes
        self.remember_session_uuid = uuid4().bytes
        self.connection.execute("INSERT INTO user_invitation VALUES (?, ?, 10, 3610, NULL)", (self.invitation_uuid, b"i" * 32))
        self.connection.execute("INSERT INTO user_account VALUES (?, 'Alice', 'alice', '$argon2id$encoded', 20, 20)", (self.user_uuid,))
        self.connection.execute("INSERT INTO ledger VALUES (?, 'Main ledger', 'ledger.sqlite', 'BookOpen', ?)", (self.ledger_uuid, b"\x80\x80\x80"))
        self.connection.execute("INSERT INTO ledger_grant VALUES (?, ?, ?, 'OWNER', 30, NULL)", (self.grant_uuid, self.user_uuid, self.ledger_uuid))
        self.connection.execute("INSERT INTO auth_session VALUES (?, ?, ?, 40, 43240, 1800, NULL)", (self.auth_session_uuid, self.user_uuid, b"s" * 32))
        self.connection.execute("INSERT INTO remember_session VALUES (?, ?, ?, 40, 2592040, NULL)", (self.remember_session_uuid, self.user_uuid, b"r" * 32))

    def tearDown(self) -> None:
        self.connection.close()
        self.temporary_directory.cleanup()

    def test_declares_every_uuid_column_as_blob(self) -> None:
        expected_columns = {
            "user_invitation": {"uuid"},
            "user_account": {"uuid"},
            "ledger": {"uuid"},
            "ledger_grant": {"uuid", "user_uuid", "ledger_uuid"},
            "mfa_method": {"uuid", "user_uuid"},
            "recovery_code": {"uuid", "user_uuid"},
            "user_preferences": {"user_uuid"},
            "auth_session": {"uuid", "user_uuid"},
            "remember_session": {"uuid", "user_uuid"},
        }
        for table, uuid_columns in expected_columns.items():
            columns = {row["name"]: row["type"] for row in self.connection.execute(f"PRAGMA table_info({table})")}
            with self.subTest(table=table):
                self.assertEqual({column: columns[column] for column in uuid_columns}, {column: "BLOB" for column in uuid_columns})

    def test_stores_uuid_as_exactly_16_bytes(self) -> None:
        row = self.connection.execute("SELECT typeof(uuid) AS storage_type, length(uuid) AS size FROM user_account").fetchone()

        self.assertEqual(row["storage_type"], "blob")
        self.assertEqual(row["size"], 16)

    def test_enforces_text_limits(self) -> None:
        invalid_updates = (
            ("user_account", "name", ""),
            ("user_account", "name", "x" * 51),
            ("ledger", "name", ""),
            ("ledger", "name", "x" * 51),
            ("ledger", "icon", ""),
            ("ledger", "icon", "x" * 51),
        )
        for table, column, value in invalid_updates:
            with self.subTest(table=table, column=column):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.connection.execute(f"UPDATE {table} SET {column} = ?", (value,))

    def test_enforces_user_timestamp_and_normalized_name_uniqueness(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("UPDATE user_account SET password_changed_at = 19")
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("INSERT INTO user_account VALUES (?, 'Other', 'alice', '$argon2id$other', 20, 20)", (uuid4().bytes,))

    def test_enforces_color_size(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("UPDATE ledger SET color_code = ?", (b"xx",))

    def test_enforces_owner_grants_and_one_active_relation(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("UPDATE ledger_grant SET role = 'READER'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("INSERT INTO ledger_grant VALUES (?, ?, ?, 'OWNER', 31, NULL)", (uuid4().bytes, self.user_uuid, self.ledger_uuid))

    def test_enforces_mfa_type(self) -> None:
        method_uuid = uuid4().bytes
        self.connection.execute("INSERT INTO mfa_method VALUES (?, ?, 'TOTP', ?, 30, NULL, NULL)", (method_uuid, self.user_uuid, b"encrypted"))
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("UPDATE mfa_method SET type = 'SMS' WHERE uuid = ?", (method_uuid,))

    def test_enforces_one_mfa_method_of_each_type_per_user(self) -> None:
        self.connection.execute("INSERT INTO mfa_method VALUES (?, ?, 'TOTP', ?, 30, NULL, NULL)", (uuid4().bytes, self.user_uuid, b"first"))

        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("INSERT INTO mfa_method VALUES (?, ?, 'TOTP', ?, 40, NULL, NULL)", (uuid4().bytes, self.user_uuid, b"second"))

    def test_enforces_recovery_code_usage_timestamp_and_one_active_code(self) -> None:
        code_uuid = uuid4().bytes
        self.connection.execute("INSERT INTO recovery_code VALUES (?, ?, ?, 30, NULL)", (code_uuid, self.user_uuid, b"c" * 32))
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("UPDATE recovery_code SET used_at = 29 WHERE uuid = ?", (code_uuid,))
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("INSERT INTO recovery_code VALUES (?, ?, ?, 31, NULL)", (uuid4().bytes, self.user_uuid, b"d" * 32))

        self.connection.execute("UPDATE recovery_code SET used_at = 40 WHERE uuid = ?", (code_uuid,))
        self.connection.execute("INSERT INTO recovery_code VALUES (?, ?, ?, 41, NULL)", (uuid4().bytes, self.user_uuid, b"d" * 32))

    def test_enforces_user_preference_limits(self) -> None:
        self.connection.execute("INSERT INTO user_preferences VALUES (?, 'DD/MM/YYYY', 'HH:mm', 'pt-BR', 'DARK', 'UTC')", (self.user_uuid,))
        invalid_updates = (("date_format", ""), ("time_format", ""), ("number_format", ""), ("theme", "SYSTEM"), ("timezone", ""))
        for column, value in invalid_updates:
            with self.subTest(column=column):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.connection.execute(f"UPDATE user_preferences SET {column} = ?", (value,))

    def test_revoked_grant_allows_a_new_active_relation(self) -> None:
        self.connection.execute("UPDATE ledger_grant SET revoked_at = 40 WHERE uuid = ?", (self.grant_uuid,))

        self.connection.execute("INSERT INTO ledger_grant VALUES (?, ?, ?, 'OWNER', 50, NULL)", (uuid4().bytes, self.user_uuid, self.ledger_uuid))

    def test_expiration_must_follow_creation(self) -> None:
        for table in ("user_invitation", "auth_session", "remember_session"):
            with self.subTest(table=table):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.connection.execute(f"UPDATE {table} SET expires_at = created_at")

    def test_auth_session_inactivity_timeout_must_be_positive(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("UPDATE auth_session SET inactivity_timeout_seconds = 0")

    def test_invitation_and_remember_session_use_must_precede_expiration(self) -> None:
        invalid_updates = (
            ("user_invitation", "consumed_at", 3610),
            ("remember_session", "last_used_at", 2592040),
        )
        for table, column, timestamp in invalid_updates:
            with self.subTest(table=table, column=column):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.connection.execute(f"UPDATE {table} SET {column} = ?", (timestamp,))

    def test_deleting_user_cascades_authentication_records_and_grants(self) -> None:
        mfa_uuid = uuid4().bytes
        recovery_uuid = uuid4().bytes
        self.connection.execute("INSERT INTO mfa_method VALUES (?, ?, 'TOTP', ?, 30, NULL, NULL)", (mfa_uuid, self.user_uuid, b"encrypted"))
        self.connection.execute("INSERT INTO recovery_code VALUES (?, ?, ?, 30, NULL)", (recovery_uuid, self.user_uuid, b"c" * 32))
        self.connection.execute("INSERT INTO user_preferences VALUES (?, NULL, NULL, NULL, 'DARK', 'UTC')", (self.user_uuid,))

        self.connection.execute("DELETE FROM user_account WHERE uuid = ?", (self.user_uuid,))

        for table in ("ledger_grant", "mfa_method", "recovery_code", "user_preferences", "auth_session", "remember_session"):
            with self.subTest(table=table):
                self.assertEqual(self.connection.execute(f"SELECT count(*) AS count FROM {table}").fetchone()["count"], 0)


if __name__ == "__main__":
    unittest.main()
