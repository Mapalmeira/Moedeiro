import sqlite3
from typing import Self

from app.application.registry.unit_of_work import RegistryUnitOfWork
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.registry.repository.ledger import SqliteLedgerRepository
from app.infrastructure.persistence.sqlite.registry.repository.ledger_token import SqliteLedgerTokenRepository

class SqliteRegistryUnitOfWork(RegistryUnitOfWork):
    def __init__(self, database: SqliteDatabase):
        self.database = database

    def __enter__(self) -> Self:
        self.connection: sqlite3.Connection = self.database.get_connection()
        self.ledger_repository = SqliteLedgerRepository(self.connection)
        self.ledger_token_repository = SqliteLedgerTokenRepository(self.connection)
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        try:
            self.rollback()
        finally:
            self.connection.close()

    def commit(self) -> None:
        self.connection.commit()

    def rollback(self) -> None:
        self.connection.rollback()
