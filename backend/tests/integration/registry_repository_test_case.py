from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.registry.repository.access_grant import SqliteAccessGrantRepository
from app.infrastructure.persistence.sqlite.registry.repository.access_invitation import SqliteAccessInvitationRepository
from app.infrastructure.persistence.sqlite.registry.repository.auth_session import SqliteAuthSessionRepository
from app.infrastructure.persistence.sqlite.registry.repository.ledger import SqliteLedgerRepository


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"


class RegistryRepositoryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.connection = SqliteDatabase(Path(self.temporary_directory.name) / "registry.sqlite").get_connection()
        self.connection.executescript(SCHEMA_PATH.read_text())
        self.ledger_repository = SqliteLedgerRepository(self.connection)
        self.invitation_repository = SqliteAccessInvitationRepository(self.connection)
        self.grant_repository = SqliteAccessGrantRepository(self.connection)
        self.session_repository = SqliteAuthSessionRepository(self.connection)

    def tearDown(self) -> None:
        self.connection.close()
        self.temporary_directory.cleanup()

    def create_ledger(self, path: str | None = None):
        if path is None:
            path = f"{uuid4()}.sqlite"
        return self.ledger_repository.create(path, "BookOpen", b"\x80\x80\x80")

    def create_invitation(self, ledger=None, secret_hash: bytes | None = None):
        if ledger is None:
            ledger = self.create_ledger()
        if secret_hash is None:
            secret_hash = ledger.uuid.bytes * 2
        return self.invitation_repository.create(ledger.uuid, secret_hash, 10, 90)

    def create_grant(self, invitation=None):
        if invitation is None:
            invitation = self.create_invitation()
        return self.grant_repository.create_webcrypto(invitation.grant_uuid, invitation.ledger_uuid, "browser", b"public-key", 20)
