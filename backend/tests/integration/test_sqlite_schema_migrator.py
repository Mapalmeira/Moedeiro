from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.migration import SchemaVersionError, SqliteSchemaMigrator


class SqliteSchemaMigratorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.database = SqliteDatabase(self.directory / "database.sqlite")
        self.migrations_directory = self.directory / "migrations"
        self.migrations_directory.mkdir()
        connection = self.database.get_connection()
        try:
            connection.executescript(
                """
                CREATE TABLE metadata(singleton INTEGER PRIMARY KEY, schema_version INTEGER NOT NULL);
                INSERT INTO metadata(singleton, schema_version) VALUES (1, 1);
                CREATE TABLE sample(value TEXT NOT NULL);
                """
            )
        finally:
            connection.close()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_applies_ordered_migrations_and_updates_the_version(self) -> None:
        (self.migrations_directory / "0002_add_number.sql").write_text(
            "ALTER TABLE sample ADD COLUMN number INTEGER;\n",
            encoding="utf-8",
        )
        (self.migrations_directory / "0003_add_index.sql").write_text(
            "CREATE INDEX sample_number_idx ON sample(number);\n",
            encoding="utf-8",
        )
        migrator = SqliteSchemaMigrator("metadata", 3, self.migrations_directory)

        self.assertEqual(migrator.migrate(self.database), 2)
        migrator.validate(self.database)

        connection = self.database.get_connection()
        try:
            version = connection.execute("SELECT schema_version FROM metadata WHERE singleton = 1").fetchone()[0]
            index = connection.execute(
                "SELECT name FROM sqlite_schema WHERE type = 'index' AND name = 'sample_number_idx'"
            ).fetchone()
        finally:
            connection.close()
        self.assertEqual(version, 3)
        self.assertIsNotNone(index)

    def test_rolls_back_schema_and_version_when_a_migration_fails(self) -> None:
        (self.migrations_directory / "0002_broken.sql").write_text(
            "ALTER TABLE sample ADD COLUMN added TEXT;\nINVALID SQL;\n",
            encoding="utf-8",
        )
        migrator = SqliteSchemaMigrator("metadata", 2, self.migrations_directory)

        with self.assertRaises(sqlite3.OperationalError):
            migrator.migrate(self.database)

        connection = self.database.get_connection()
        try:
            version = connection.execute("SELECT schema_version FROM metadata WHERE singleton = 1").fetchone()[0]
            columns = [row[1] for row in connection.execute("PRAGMA table_info(sample)").fetchall()]
        finally:
            connection.close()
        self.assertEqual(version, 1)
        self.assertNotIn("added", columns)

    def test_rejects_a_missing_migration_in_the_version_sequence(self) -> None:
        migrator = SqliteSchemaMigrator("metadata", 2, self.migrations_directory)

        with self.assertRaisesRegex(SchemaVersionError, "expected one migration"):
            migrator.migrate(self.database)

    def test_rejects_a_database_created_by_a_newer_release(self) -> None:
        connection = self.database.get_connection()
        try:
            connection.execute("UPDATE metadata SET schema_version = 3")
            connection.commit()
        finally:
            connection.close()
        migrator = SqliteSchemaMigrator("metadata", 2, self.migrations_directory)

        with self.assertRaisesRegex(SchemaVersionError, "only supports up to 2"):
            migrator.validate(self.database)


if __name__ == "__main__":
    unittest.main()
