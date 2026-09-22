"""SQLite transactional wrapper whose registry repositories share one connection."""

import sqlite3

from typing_extensions import Self

from app.application.registry.unit_of_work import RegistryUnitOfWork
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.registry.repository.auth_session import SqliteAuthSessionRepository
from app.infrastructure.persistence.sqlite.registry.repository.ledger import SqliteLedgerRepository
from app.infrastructure.persistence.sqlite.registry.repository.ledger_grant import SqliteLedgerGrantRepository
from app.infrastructure.persistence.sqlite.registry.repository.ledger_token_grant import SqliteLedgerTokenGrantRepository
from app.infrastructure.persistence.sqlite.registry.repository.mfa_method import SqliteMfaMethodRepository
from app.infrastructure.persistence.sqlite.registry.repository.recovery_code import SqliteRecoveryCodeRepository
from app.infrastructure.persistence.sqlite.registry.repository.registry_metadata import SqliteRegistryMetadataRepository
from app.infrastructure.persistence.sqlite.registry.repository.remember_session import SqliteRememberSessionRepository
from app.infrastructure.persistence.sqlite.registry.repository.user import SqliteUserRepository
from app.infrastructure.persistence.sqlite.registry.repository.user_invitation import SqliteUserInvitationRepository
from app.infrastructure.persistence.sqlite.registry.repository.user_preferences import SqliteUserPreferencesRepository


class SqliteRegistryUnitOfWork(RegistryUnitOfWork):
    def __init__(self, database: SqliteDatabase):
        self.database = database

    def __enter__(self) -> Self:
        self.connection: sqlite3.Connection = self.database.get_connection()
        self.registry_metadata_repository = SqliteRegistryMetadataRepository(self.connection)
        self.ledger_repository = SqliteLedgerRepository(self.connection)
        self.user_repository = SqliteUserRepository(self.connection)
        self.user_invitation_repository = SqliteUserInvitationRepository(self.connection)
        self.ledger_grant_repository = SqliteLedgerGrantRepository(self.connection)
        self.ledger_token_grant_repository = SqliteLedgerTokenGrantRepository(self.connection)
        self.mfa_method_repository = SqliteMfaMethodRepository(self.connection)
        self.recovery_code_repository = SqliteRecoveryCodeRepository(self.connection)
        self.user_preferences_repository = SqliteUserPreferencesRepository(self.connection)
        self.auth_session_repository = SqliteAuthSessionRepository(self.connection)
        self.remember_session_repository = SqliteRememberSessionRepository(self.connection)
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
