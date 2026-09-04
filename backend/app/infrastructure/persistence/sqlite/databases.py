from pathlib import Path
from time import time_ns
from uuid import UUID

from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.ledger.schema_version import CURRENT_LEDGER_SCHEMA_VERSION
from app.infrastructure.persistence.sqlite.ledger.unit_of_work import SqliteLedgerUnitOfWork
from app.infrastructure.persistence.sqlite.migration import SqliteSchemaMigrator
from app.infrastructure.persistence.sqlite.registry.schema_version import CURRENT_REGISTRY_SCHEMA_VERSION
from app.infrastructure.persistence.sqlite.registry.unit_of_work import SqliteRegistryUnitOfWork


class SqliteDatabases:
    def __init__(
        self,
        registry_db_path: Path,
        registry_schema_path: Path,
        ledger_dbs_dir: Path,
        ledger_schema_path: Path,
    ):
        self.registry_database = SqliteDatabase(registry_db_path)
        self.registry_schema_path = registry_schema_path
        self.ledger_dbs_dir = ledger_dbs_dir
        self.ledger_schema_path = ledger_schema_path
        self.registry_migrator = SqliteSchemaMigrator(
            "registry_metadata",
            CURRENT_REGISTRY_SCHEMA_VERSION,
            registry_schema_path.parent / "migrations",
        )
        self.ledger_migrator = SqliteSchemaMigrator(
            "ledger_metadata",
            CURRENT_LEDGER_SCHEMA_VERSION,
            ledger_schema_path.parent / "migrations",
        )

    def initialize(self) -> None:
        self._initialize_storage()
        ledger_paths = self._ledger_paths()
        registry_requires_migration = self.registry_migrator.requires_migration(self.registry_database)
        ledgers_requiring_migration = [
            path for path in ledger_paths if self.ledger_migrator.requires_migration(SqliteDatabase(path))
        ]
        if registry_requires_migration or ledgers_requiring_migration:
            backup_timestamp = time_ns()
            if registry_requires_migration:
                self._backup_database(
                    self.registry_database,
                    self.registry_database.path.parent / "backups",
                    backup_timestamp,
                )
            for ledger_path in ledgers_requiring_migration:
                self._backup_database(
                    SqliteDatabase(ledger_path),
                    self.ledger_dbs_dir / "backup",
                    backup_timestamp,
                )
        if registry_requires_migration:
            self.registry_migrator.migrate(self.registry_database)
        for ledger_path in ledgers_requiring_migration:
            self.ledger_migrator.migrate(SqliteDatabase(ledger_path))
        self.registry_migrator.validate(self.registry_database)
        for ledger_path in ledger_paths:
            self.ledger_migrator.validate(SqliteDatabase(ledger_path))
        self.registry_database.enable_wal()
        for ledger_path in ledger_paths:
            SqliteDatabase(ledger_path).enable_wal()

    def _initialize_storage(self) -> None:
        self.ledger_dbs_dir.mkdir(parents=True, exist_ok=True)
        if not self.registry_database.path.exists():
            database_initialized = False
            try:
                self.registry_database = SqliteDatabase.initialize(
                    self.registry_database.path,
                    self.registry_schema_path,
                )
                database_initialized = True
                with self.open_registry() as unit_of_work:
                    unit_of_work.registry_metadata_repository.create(CURRENT_REGISTRY_SCHEMA_VERSION)
                    unit_of_work.commit()
            except Exception:
                if database_initialized:
                    self.registry_database.path.unlink(missing_ok=True)
                raise

    def get_ledger_path(self, ledger_uuid: UUID) -> Path:
        return self.ledger_dbs_dir / f"{ledger_uuid}.sqlite"

    def delete_ledger_database(self, path: str | Path) -> None:
        self._resolve_ledger_path(path).unlink(missing_ok=True)

    def initialize_ledger(self, ledger_uuid: UUID, created_at: int) -> Path:
        path = self.get_ledger_path(ledger_uuid)
        database_initialized = False
        try:
            database = SqliteDatabase.initialize(path, self.ledger_schema_path)
            database_initialized = True
            with SqliteLedgerUnitOfWork(database) as unit_of_work:
                unit_of_work.ledger_metadata_repository.create(ledger_uuid, CURRENT_LEDGER_SCHEMA_VERSION, created_at)
                unit_of_work.commit()
            database.enable_wal()
        except Exception:
            if database_initialized:
                path.unlink(missing_ok=True)
            raise
        return path

    def open_registry(self) -> SqliteRegistryUnitOfWork:
        return SqliteRegistryUnitOfWork(self.registry_database)

    def open_ledger(self, path: str | Path) -> SqliteLedgerUnitOfWork:
        ledger_path = self._resolve_ledger_path(path)
        if not ledger_path.is_file():
            raise FileNotFoundError(ledger_path)
        return SqliteLedgerUnitOfWork(SqliteDatabase(ledger_path))

    def _ledger_paths(self) -> list[Path]:
        return list(self.ledger_dbs_dir.glob("*.sqlite"))

    @staticmethod
    def _backup_database(database: SqliteDatabase, directory: Path, timestamp: int) -> None:
        database.backup_to(directory / f"{timestamp}-{database.path.name}")

    def _resolve_ledger_path(self, path: str | Path) -> Path:
        directory = self.ledger_dbs_dir.resolve()
        supplied_path = Path(path)
        if not supplied_path.is_absolute():
            supplied_path = directory / supplied_path
        ledger_path = supplied_path.resolve()
        if ledger_path.parent != directory:
            raise ValueError("ledger database must be directly inside LEDGER_DBS_DIR")
        return ledger_path
