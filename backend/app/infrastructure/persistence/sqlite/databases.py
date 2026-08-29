from pathlib import Path
from uuid import UUID

from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.ledger.unit_of_work import SqliteLedgerUnitOfWork
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

    def initialize(self) -> None:
        self.ledger_dbs_dir.mkdir(parents=True, exist_ok=True)
        if not self.registry_database.path.exists():
            self.registry_database = SqliteDatabase.initialize(
                self.registry_database.path,
                self.registry_schema_path,
            )

    def get_ledger_path(self, ledger_uuid: UUID) -> Path:
        return self.ledger_dbs_dir / f"{ledger_uuid}.sqlite"

    def initialize_ledger(self, ledger_uuid: UUID, name: str, schema_version: int) -> Path:
        path = self.get_ledger_path(ledger_uuid)
        database_initialized = False
        try:
            database = SqliteDatabase.initialize(path, self.ledger_schema_path)
            database_initialized = True
            with SqliteLedgerUnitOfWork(database) as unit_of_work:
                unit_of_work.ledger_metadata_repository.create(ledger_uuid, name, schema_version)
                unit_of_work.commit()
        except Exception:
            if database_initialized:
                path.unlink(missing_ok=True)
            raise
        return path

    def open_registry(self) -> SqliteRegistryUnitOfWork:
        return SqliteRegistryUnitOfWork(self.registry_database)

    def open_ledger(self, path: str | Path) -> SqliteLedgerUnitOfWork:
        directory = self.ledger_dbs_dir.resolve()
        supplied_path = Path(path)
        if not supplied_path.is_absolute():
            supplied_path = directory / supplied_path
        ledger_path = supplied_path.resolve()
        if ledger_path.parent != directory:
            raise ValueError("ledger database must be directly inside LEDGER_DBS_DIR")
        if not ledger_path.is_file():
            raise FileNotFoundError(ledger_path)
        return SqliteLedgerUnitOfWork(SqliteDatabase(ledger_path))
