from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.databases import SqliteDatabases
from app.infrastructure.persistence.sqlite.ledger.schema_version import CURRENT_LEDGER_SCHEMA_VERSION
from app.infrastructure.persistence.sqlite.migration import SchemaVersionError, SqliteSchemaMigrator
from app.infrastructure.persistence.sqlite.registry.schema_version import CURRENT_REGISTRY_SCHEMA_VERSION


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
            self.assertEqual(unit_of_work.ledger_repository.list_all("name", True), [])
            metadata = unit_of_work.registry_metadata_repository.get()
        assert metadata is not None
        self.assertEqual(metadata.schema_version, CURRENT_REGISTRY_SCHEMA_VERSION)

        connection = sqlite3.connect(self.registry_db_path)
        try:
            self.assertEqual(connection.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        finally:
            connection.close()

    def test_initialize_preserves_an_existing_registry(self) -> None:
        self.databases.initialize()
        with self.databases.open_registry() as unit_of_work:
            ledger_uuid = uuid4()
            ledger_path = self.databases.initialize_ledger(ledger_uuid, 10, "pt-BR")
            ledger = unit_of_work.ledger_repository.create(ledger_uuid, "Existing", ledger_path.name, "lucide:BookOpen", b"\x80\x80\x80", 10)
            unit_of_work.commit()

        self.databases.initialize()

        with self.databases.open_registry() as unit_of_work:
            self.assertEqual(unit_of_work.ledger_repository.get(ledger.uuid), ledger)

    def test_initialize_enables_wal_for_an_existing_registry(self) -> None:
        SqliteDatabase.initialize(self.registry_db_path, REGISTRY_SCHEMA_PATH)
        connection = sqlite3.connect(self.registry_db_path)
        try:
            connection.execute(
                "INSERT INTO registry_metadata(singleton, schema_version) VALUES (1, ?)",
                (CURRENT_REGISTRY_SCHEMA_VERSION,),
            )
            connection.commit()
        finally:
            connection.close()

        self.databases.initialize()

        connection = sqlite3.connect(self.registry_db_path)
        try:
            self.assertEqual(connection.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        finally:
            connection.close()

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

    def test_initialize_ledger_applies_the_schema_and_creates_metadata_and_default_currencies(self) -> None:
        self.databases.initialize()
        ledger_uuid = uuid4()

        path = self.databases.initialize_ledger(ledger_uuid, 100, "pt-BR")

        self.assertEqual(path, self.ledger_dbs_dir / f"{ledger_uuid}.sqlite")
        with self.databases.open_ledger(path) as unit_of_work:
            metadata = unit_of_work.ledger_metadata_repository.get()
            currencies = unit_of_work.currency_repository.list_all()
            assert metadata is not None
        self.assertEqual(
            [
                (currency.name, currency.prefix, currency.suffix, currency.decimal_places, currency.icon, currency.color_code)
                for currency in sorted(currencies, key=lambda currency: currency.name)
            ],
            [
                ("Bitcoin", None, " BTC", 8, "lucide:Bitcoin", bytes.fromhex("AE5400")),
                ("Dólar americano", "US$ ", None, 2, "lucide:DollarSign", bytes.fromhex("2563EB")),
                ("Euro", "€ ", None, 2, "lucide:Euro", bytes.fromhex("003399")),
                ("Iene japonês", "¥ ", None, 0, "lucide:JapaneseYen", bytes.fromhex("BC002D")),
                ("Libra esterlina", "£ ", None, 2, "lucide:PoundSterling", bytes.fromhex("5B2C6F")),
                ("Real", "R$ ", None, 2, "unicode:R$", bytes.fromhex("16A34A")),
            ],
        )
        self.assertEqual(metadata.ledger_uuid, ledger_uuid)
        self.assertEqual(metadata.schema_version, CURRENT_LEDGER_SCHEMA_VERSION)
        self.assertEqual(metadata.created_at, 100)
        connection = sqlite3.connect(path)
        try:
            self.assertEqual(connection.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        finally:
            connection.close()

    def test_initialize_ledger_uses_the_requested_language_for_defaults(self) -> None:
        self.databases.initialize()

        path = self.databases.initialize_ledger(uuid4(), 100, "en")

        with self.databases.open_ledger(path) as unit_of_work:
            currency_names = [currency.name for currency in unit_of_work.currency_repository.list_all()]
            category_names = [node.category.name for node in unit_of_work.category_repository.get_tree(200)]

        self.assertIn("Brazilian real", currency_names)
        self.assertIn("US dollar", currency_names)
        self.assertIn("Food", category_names)
        self.assertIn("Taxes", category_names)

    def test_initialize_enables_wal_for_an_existing_ledger(self) -> None:
        self.databases.initialize()
        ledger_uuid = uuid4()
        path = self.databases.initialize_ledger(ledger_uuid, 100, "pt-BR")
        connection = sqlite3.connect(path)
        try:
            connection.execute("PRAGMA journal_mode = DELETE")
        finally:
            connection.close()

        self.databases.initialize()

        connection = sqlite3.connect(path)
        try:
            self.assertEqual(connection.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        finally:
            connection.close()

    def test_initialize_ledger_never_overwrites_an_existing_database(self) -> None:
        self.databases.initialize()
        ledger_uuid = uuid4()
        path = self.databases.initialize_ledger(ledger_uuid, 100, "pt-BR")

        with self.assertRaises(FileExistsError):
            self.databases.initialize_ledger(ledger_uuid, 100, "pt-BR")

        self.assertTrue(path.is_file())
        with self.databases.open_ledger(path) as unit_of_work:
            metadata = unit_of_work.ledger_metadata_repository.get()
            assert metadata is not None
            self.assertEqual(metadata.ledger_uuid, ledger_uuid)

    def test_initialize_rejects_a_registry_without_schema_metadata(self) -> None:
        self.registry_db_path.parent.mkdir(parents=True)
        sqlite3.connect(self.registry_db_path).close()

        with self.assertRaisesRegex(SchemaVersionError, "no valid schema metadata"):
            self.databases.initialize()

    def test_initialize_ledger_removes_a_new_database_when_metadata_creation_fails(self) -> None:
        self.databases.initialize()
        ledger_uuid = uuid4()
        path = self.databases.get_ledger_path(ledger_uuid)

        with patch(
            "app.infrastructure.persistence.sqlite.ledger.repository.ledger_metadata.SqliteLedgerMetadataRepository.create",
            side_effect=RuntimeError("metadata failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "metadata failed"):
                self.databases.initialize_ledger(ledger_uuid, 100, "pt-BR")

        self.assertFalse(path.exists())

    def test_initialize_ledger_removes_a_new_database_when_default_currency_creation_fails(self) -> None:
        self.databases.initialize()
        ledger_uuid = uuid4()
        path = self.databases.get_ledger_path(ledger_uuid)

        with patch(
            "app.infrastructure.persistence.sqlite.ledger.repository.currency.SqliteCurrencyRepository.create",
            side_effect=RuntimeError("currency failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "currency failed"):
                self.databases.initialize_ledger(ledger_uuid, 100, "pt-BR")

        self.assertFalse(path.exists())

    def test_initialize_backs_up_only_the_registry_when_only_it_requires_a_migration(self) -> None:
        self.databases.initialize()
        ledger_uuid = uuid4()
        self.databases.initialize_ledger(ledger_uuid, 10, "pt-BR")
        migrations_directory = self.directory / "registry_migrations"
        migrations_directory.mkdir()
        (migrations_directory / "0002_add_marker.sql").write_text(
            "ALTER TABLE registry_metadata ADD COLUMN marker TEXT;\n",
            encoding="utf-8",
        )
        self.databases.registry_migrator = SqliteSchemaMigrator(
            "registry_metadata",
            2,
            migrations_directory,
        )

        self.databases.initialize()

        connection = sqlite3.connect(self.registry_db_path)
        try:
            self.assertEqual(
                connection.execute("SELECT schema_version FROM registry_metadata WHERE singleton = 1").fetchone()[0],
                2,
            )
            self.assertIn(
                "marker",
                {row[1] for row in connection.execute("PRAGMA table_info(registry_metadata)").fetchall()},
            )
        finally:
            connection.close()
        registry_backups = list((self.registry_db_path.parent / "backups").iterdir())
        self.assertEqual(len(registry_backups), 1)
        self.assertFalse((self.ledger_dbs_dir / "backup").exists())
        connection = sqlite3.connect(registry_backups[0])
        try:
            self.assertEqual(
                connection.execute("SELECT schema_version FROM registry_metadata WHERE singleton = 1").fetchone()[0],
                1,
            )
        finally:
            connection.close()

    def test_initialize_rejects_a_ledger_from_a_newer_release(self) -> None:
        self.databases.initialize()
        ledger_uuid = uuid4()
        ledger_path = self.databases.initialize_ledger(ledger_uuid, 10, "pt-BR")
        with self.databases.open_registry() as unit_of_work:
            unit_of_work.ledger_repository.create(
                ledger_uuid,
                "Future",
                ledger_path.name,
                "lucide:BookOpen",
                b"\x80\x80\x80",
                10,
            )
            unit_of_work.commit()
        connection = sqlite3.connect(ledger_path)
        try:
            connection.execute(
                "UPDATE ledger_metadata SET schema_version = ?",
                (CURRENT_LEDGER_SCHEMA_VERSION + 1,),
            )
            connection.commit()
        finally:
            connection.close()

        with self.assertRaisesRegex(SchemaVersionError, "only supports up to"):
            self.databases.initialize()

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
