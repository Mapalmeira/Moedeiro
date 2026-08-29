"""SQLite transactional wrapper whose registry repositories share one connection."""

import sqlite3
from typing import Self

from app.application.registry.unit_of_work import RegistryUnitOfWork
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.registry.repository.access_grant import SqliteAccessGrantRepository
from app.infrastructure.persistence.sqlite.registry.repository.access_invitation import SqliteAccessInvitationRepository
from app.infrastructure.persistence.sqlite.registry.repository.auth_session import SqliteAuthSessionRepository
from app.infrastructure.persistence.sqlite.registry.repository.ledger import SqliteLedgerRepository


class SqliteRegistryUnitOfWork(RegistryUnitOfWork):
    def __init__(self, database: SqliteDatabase):
        self.database = database

    def __enter__(self) -> Self:
        self.connection: sqlite3.Connection = self.database.get_connection()
        self.ledger_repository = SqliteLedgerRepository(self.connection)
        self.access_invitation_repository = SqliteAccessInvitationRepository(self.connection)
        self.access_grant_repository = SqliteAccessGrantRepository(self.connection)
        self.auth_session_repository = SqliteAuthSessionRepository(self.connection)
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
