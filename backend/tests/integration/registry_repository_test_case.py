from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.registry.repository.auth_session import SqliteAuthSessionRepository
from app.infrastructure.persistence.sqlite.registry.repository.ledger import SqliteLedgerRepository
from app.infrastructure.persistence.sqlite.registry.repository.ledger_grant import SqliteLedgerGrantRepository
from app.infrastructure.persistence.sqlite.registry.repository.mfa_method import SqliteMfaMethodRepository
from app.infrastructure.persistence.sqlite.registry.repository.recovery_code import SqliteRecoveryCodeRepository
from app.infrastructure.persistence.sqlite.registry.repository.remember_session import SqliteRememberSessionRepository
from app.infrastructure.persistence.sqlite.registry.repository.user import SqliteUserRepository
from app.infrastructure.persistence.sqlite.registry.repository.user_invitation import SqliteUserInvitationRepository
from app.infrastructure.persistence.sqlite.registry.repository.user_preferences import SqliteUserPreferencesRepository


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"


class RegistryRepositoryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.connection = SqliteDatabase(Path(self.temporary_directory.name) / "registry.sqlite").get_connection()
        self.connection.executescript(SCHEMA_PATH.read_text())
        self.ledger_repository = SqliteLedgerRepository(self.connection)
        self.user_repository = SqliteUserRepository(self.connection)
        self.invitation_repository = SqliteUserInvitationRepository(self.connection)
        self.grant_repository = SqliteLedgerGrantRepository(self.connection)
        self.mfa_repository = SqliteMfaMethodRepository(self.connection)
        self.recovery_code_repository = SqliteRecoveryCodeRepository(self.connection)
        self.preferences_repository = SqliteUserPreferencesRepository(self.connection)
        self.session_repository = SqliteAuthSessionRepository(self.connection)
        self.remember_session_repository = SqliteRememberSessionRepository(self.connection)

    def tearDown(self) -> None:
        self.connection.close()
        self.temporary_directory.cleanup()

    def create_invitation(self, secret_hash: bytes | None = None):
        if secret_hash is None:
            secret_hash = uuid4().bytes * 2
        return self.invitation_repository.create(secret_hash, 10, 100)

    def create_user(self, name: str | None = None, secret_hash: bytes | None = None):
        invitation = self.create_invitation(secret_hash)
        if name is None:
            name = f"user-{invitation.uuid}"
        user = self.user_repository.create(name, "$argon2id$test", 20)
        self.invitation_repository.consume(invitation.uuid, 20)
        return user

    def create_ledger(self, path: str | None = None, name: str = "Ledger"):
        if path is None:
            path = f"{uuid4()}.sqlite"
        return self.ledger_repository.create(uuid4(), name, path, "BookOpen", b"\x80\x80\x80")

    def create_grant(self, user=None, ledger=None, role="OWNER"):
        if user is None:
            user = self.create_user()
        if ledger is None:
            ledger = self.create_ledger()
        return self.grant_repository.create(user.uuid, ledger.uuid, role, 30)
