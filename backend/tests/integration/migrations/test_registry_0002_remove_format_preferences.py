import unittest
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from uuid import uuid4

from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.migration import SqliteSchemaMigrator
from tests.integration.migrations.fixture import create_database_from_schema_fixture


MIGRATIONS_DIRECTORY = (
    Path(__file__).resolve().parents[3]
    / "app/infrastructure/persistence/sqlite/registry/schema/migrations"
)


class RegistryRemoveFormatPreferencesMigrationTest(unittest.TestCase):
    def test_v2_removes_format_preferences_and_preserves_locale_independent_values(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "registry.sqlite"
            create_database_from_schema_fixture("registry_v1.sql", path)

            user_uuid = uuid4()
            connection = sqlite3.connect(path)
            try:
                connection.execute("PRAGMA foreign_keys = ON")
                connection.execute("INSERT INTO registry_metadata VALUES (1, 1)")
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
                foreign_key_violations = connection.execute("PRAGMA foreign_key_check").fetchall()
            finally:
                connection.close()

            self.assertEqual(columns, ["user_uuid", "language", "theme", "timezone"])
            self.assertEqual(stored, ("en", "DARK", "America/New_York"))
            self.assertEqual(version, 2)
            self.assertEqual(foreign_key_violations, [])
