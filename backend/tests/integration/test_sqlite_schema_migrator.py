import unittest
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from unittest.mock import patch

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

    def test_validate_rejects_an_older_schema(self) -> None:
        migrator = SqliteSchemaMigrator("metadata", 2, self.migrations_directory)

        with self.assertRaisesRegex(SchemaVersionError, "uses an older schema version"):
            migrator.validate(self.database)

    def test_migrate_rejects_a_newer_schema(self) -> None:
        connection = self.database.get_connection()
        try:
            connection.execute("UPDATE metadata SET schema_version = 3")
            connection.commit()
        finally:
            connection.close()

        with self.assertRaisesRegex(SchemaVersionError, "only supports up to 2"):
            SqliteSchemaMigrator("metadata", 2, self.migrations_directory).migrate(self.database)

    def test_rejects_metadata_table_without_the_singleton_row(self) -> None:
        connection = self.database.get_connection()
        try:
            connection.execute("DELETE FROM metadata")
            connection.commit()
        finally:
            connection.close()

        with self.assertRaisesRegex(SchemaVersionError, "has no valid schema metadata"):
            SqliteSchemaMigrator("metadata", 1, self.migrations_directory).validate(self.database)

    def test_rejects_a_database_without_the_metadata_table(self) -> None:
        connection = self.database.get_connection()
        try:
            connection.execute("DROP TABLE metadata")
            connection.commit()
        finally:
            connection.close()

        with self.assertRaisesRegex(SchemaVersionError, "has no valid schema metadata"):
            SqliteSchemaMigrator("metadata", 1, self.migrations_directory).validate(self.database)

    def test_rolls_back_when_schema_version_changes_during_migration(self) -> None:
        migration = self.migrations_directory / "0002_change.sql"
        migration.write_text("SELECT 1;\n", encoding="utf-8")
        migrator = SqliteSchemaMigrator("metadata", 2, self.migrations_directory)

        def change_version(connection, script) -> None:
            connection.execute("UPDATE metadata SET schema_version = 99")

        with patch.object(migrator, "_execute_script", side_effect=change_version):
            with self.assertRaisesRegex(SchemaVersionError, "changed while it was being migrated"):
                migrator.migrate(self.database)

        self.assertTrue(migrator.requires_migration(self.database))

    def test_rejects_an_incomplete_final_sql_statement(self) -> None:
        connection = self.database.get_connection()
        try:
            with self.assertRaisesRegex(SchemaVersionError, "incomplete SQL statement"):
                SqliteSchemaMigrator._execute_script(connection, "CREATE TABLE unfinished(")
        finally:
            connection.close()
