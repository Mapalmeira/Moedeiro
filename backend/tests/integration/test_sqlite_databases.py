from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.databases import SqliteDatabases


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class SqliteDatabasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.registry_db_path = self.directory / "registry/registry.sqlite"
        self.ledger_dbs_dir = self.directory / "ledgers"
        self.databases = SqliteDatabases(
            self.registry_db_path,
            REGISTRY_SCHEMA_PATH,
            self.ledger_dbs_dir,
            LEDGER_SCHEMA_PATH,
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_initialize_creates_an_empty_registry_and_the_ledger_directory(self) -> None:
        self.databases.initialize()

        self.assertTrue(self.registry_db_path.is_file())
        self.assertTrue(self.ledger_dbs_dir.is_dir())
        with self.databases.open_registry() as unit_of_work:
            self.assertEqual(unit_of_work.ledger_repository.list_all(), [])

    def test_initialize_preserves_an_existing_registry(self) -> None:
        self.databases.initialize()
        with self.databases.open_registry() as unit_of_work:
            ledger = unit_of_work.ledger_repository.create("Existing", "existing.sqlite", "BookOpen", b"\x80\x80\x80")
            unit_of_work.commit()

        self.databases.initialize()

        with self.databases.open_registry() as unit_of_work:
            self.assertEqual(unit_of_work.ledger_repository.get(ledger.uuid), ledger)

    def test_database_initialization_removes_the_file_when_the_schema_fails(self) -> None:
        database_path = self.directory / "failed.sqlite"
        invalid_schema_path = self.directory / "invalid.sql"
        invalid_schema_path.write_text("INVALID SQL", encoding="utf-8")

        with self.assertRaises(sqlite3.OperationalError):
            SqliteDatabase.initialize(database_path, invalid_schema_path)

        self.assertFalse(database_path.exists())

    def test_database_initialization_returns_the_initialized_database(self) -> None:
        database_path = self.directory / "created.sqlite"
        schema_path = self.directory / "schema.sql"
        schema_path.write_text("CREATE TABLE sample(value INTEGER);", encoding="utf-8")

        database = SqliteDatabase.initialize(database_path, schema_path)

        self.assertEqual(database.path, database_path)
        connection = database.get_connection()
        try:
            table = connection.execute(
                "SELECT name FROM sqlite_schema WHERE type = 'table' AND name = 'sample'"
            ).fetchone()
        finally:
            connection.close()
        self.assertIsNotNone(table)

    def test_initialize_ledger_applies_the_schema_and_creates_metadata(self) -> None:
        self.databases.initialize()
        ledger_uuid = uuid4()

        path = self.databases.initialize_ledger(ledger_uuid, 1)

        self.assertEqual(path, self.ledger_dbs_dir / f"{ledger_uuid}.sqlite")
        with self.databases.open_ledger(path) as unit_of_work:
            metadata = unit_of_work.ledger_metadata_repository.get()
            assert metadata is not None
            self.assertEqual(metadata.ledger_uuid, ledger_uuid)
            self.assertEqual(metadata.schema_version, 1)

    def test_initialize_ledger_never_overwrites_an_existing_database(self) -> None:
        self.databases.initialize()
        ledger_uuid = uuid4()
        path = self.databases.initialize_ledger(ledger_uuid, 1)

        with self.assertRaises(FileExistsError):
            self.databases.initialize_ledger(ledger_uuid, 1)

        self.assertTrue(path.is_file())
        with self.databases.open_ledger(path) as unit_of_work:
            metadata = unit_of_work.ledger_metadata_repository.get()
            assert metadata is not None
            self.assertEqual(metadata.ledger_uuid, ledger_uuid)

    def test_initialize_ledger_removes_a_new_database_when_schema_version_is_invalid(self) -> None:
        self.databases.initialize()
        ledger_uuid = uuid4()
        path = self.databases.get_ledger_path(ledger_uuid)

        with self.assertRaises(ValidationError):
            self.databases.initialize_ledger(ledger_uuid, 0)

        self.assertFalse(path.exists())

    def test_open_ledger_rejects_paths_outside_the_configured_directory(self) -> None:
        self.databases.initialize()
        outside_path = self.directory / "outside.sqlite"
        SqliteDatabase.initialize(outside_path, LEDGER_SCHEMA_PATH)

        with self.assertRaises(ValueError):
            self.databases.open_ledger(outside_path)

    def test_open_ledger_does_not_create_a_missing_database(self) -> None:
        self.databases.initialize()
        missing_path = self.ledger_dbs_dir / "missing.sqlite"

        with self.assertRaises(FileNotFoundError):
            self.databases.open_ledger(missing_path)

        self.assertFalse(missing_path.exists())


if __name__ == "__main__":
    unittest.main()
