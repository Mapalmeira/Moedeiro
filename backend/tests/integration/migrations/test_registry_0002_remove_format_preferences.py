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


class RegistryRemoveFormatPreferencesMigrationTest(unittest.TestCase):
    def test_v2_removes_format_preferences_and_preserves_locale_independent_values(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "registry.sqlite"
            user_uuid = uuid4()
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
                    CREATE TABLE user_preferences (
                        user_uuid BLOB PRIMARY KEY,
                        language TEXT NOT NULL,
                        date_format TEXT NOT NULL CHECK (date_format IN ('DMY', 'MDY', 'YMD')),
                        time_format TEXT NOT NULL CHECK (time_format IN ('H12', 'H24')),
                        number_format TEXT NOT NULL CHECK (number_format IN ('COMMA', 'DOT')),
                        theme TEXT NOT NULL CHECK (theme IN ('LIGHT', 'DARK')),
                        timezone TEXT NOT NULL CHECK (length(timezone) BETWEEN 1 AND 50),
                        FOREIGN KEY (user_uuid) REFERENCES user_account(uuid) ON DELETE CASCADE
                    ) STRICT;
                    INSERT INTO registry_metadata(singleton, schema_version) VALUES (1, 1);
                    """
                )
                connection.execute(
                    "INSERT INTO user_account VALUES (?, 'Alice', 'alice', '$argon2id$test', 10, 10)",
                    (user_uuid.bytes,),
                )
                connection.execute(
                    "INSERT INTO user_preferences VALUES (?, 'en', 'MDY', 'H12', 'DOT', 'DARK', 'America/New_York')",
                    (user_uuid.bytes,),
                )
                connection.commit()
            finally:
                connection.close()

            migrator = SqliteSchemaMigrator("registry_metadata", 2, MIGRATIONS_DIRECTORY)
            self.assertEqual(migrator.migrate(SqliteDatabase(path)), 1)

            connection = sqlite3.connect(path)
            try:
                columns = [row[1] for row in connection.execute("PRAGMA table_info(user_preferences)")]
                stored = connection.execute(
                    "SELECT language, theme, timezone FROM user_preferences WHERE user_uuid = ?",
                    (user_uuid.bytes,),
                ).fetchone()
                version = connection.execute(
                    "SELECT schema_version FROM registry_metadata WHERE singleton = 1"
                ).fetchone()[0]
            finally:
                connection.close()

            self.assertEqual(columns, ["user_uuid", "language", "theme", "timezone"])
            self.assertEqual(stored, ("en", "DARK", "America/New_York"))
            self.assertEqual(version, 2)


if __name__ == "__main__":
    unittest.main()
