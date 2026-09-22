import unittest
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

from app.application.registry.use_cases.user_invitation import create_user_invitation, get_available_user_invitation, list_user_invitations, revoke_user_invitation
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.registry.unit_of_work import SqliteRegistryUnitOfWork


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"


class RegistryInvitationUseCasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.database = SqliteDatabase.initialize(Path(self.temporary_directory.name) / "registry.sqlite", SCHEMA_PATH)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def open_registry(self) -> SqliteRegistryUnitOfWork:
        return SqliteRegistryUnitOfWork(self.database)

    @patch("app.domain.registry.model.crockford_code.secrets.token_bytes", return_value=bytes(range(10)))
    def test_create_generates_80_bit_crockford_code_and_persists_only_its_hash(self, token_bytes) -> None:
        code = create_user_invitation(self.open_registry, 100)

        self.assertEqual(code, "000G40R40M30E209")
        with self.open_registry() as unit_of_work:
            invitation = unit_of_work.user_invitation_repository.get_by_secret_hash(hashlib.sha256(code.encode("ascii")).digest())
        assert invitation is not None
        self.assertEqual(invitation.secret_hash, hashlib.sha256(code.encode("ascii")).digest())
        self.assertEqual(invitation.expires_at, 3700)
        token_bytes.assert_called_once_with(10)

    def test_create_rejects_nonpositive_expiration(self) -> None:
        for expiration_seconds in (0, -1):
            with self.subTest(expiration_seconds=expiration_seconds):
                with self.assertRaises(ValueError):
                    create_user_invitation(self.open_registry, 100, expiration_seconds)

    def test_get_returns_only_an_invitation_active_at_the_timestamp(self) -> None:
        with patch("app.domain.registry.model.crockford_code.secrets.token_bytes", return_value=b"a" * 10):
            code = create_user_invitation(self.open_registry, 100, 100)
        with self.open_registry() as unit_of_work:
            invitation = unit_of_work.user_invitation_repository.get_by_secret_hash(hashlib.sha256(code.encode("ascii")).digest())
        assert invitation is not None

        self.assertIsNone(get_available_user_invitation(self.open_registry, code, 99))
        self.assertEqual(get_available_user_invitation(self.open_registry, code, 100), invitation)
        self.assertEqual(get_available_user_invitation(self.open_registry, code, 199), invitation)
        self.assertIsNone(get_available_user_invitation(self.open_registry, code, 200))
        self.assertIsNone(get_available_user_invitation(self.open_registry, "0" * 16, 150))

    def test_revoke_deletes_an_available_invitation_only_once(self) -> None:
        code = create_user_invitation(self.open_registry, 100)
        with self.open_registry() as unit_of_work:
            invitation = unit_of_work.user_invitation_repository.get_by_secret_hash(hashlib.sha256(code.encode("ascii")).digest())
        assert invitation is not None

        self.assertTrue(revoke_user_invitation(self.open_registry, invitation.uuid))
        self.assertFalse(revoke_user_invitation(self.open_registry, invitation.uuid))
        self.assertIsNone(get_available_user_invitation(self.open_registry, code, 170))
        self.assertEqual(list_user_invitations(self.open_registry, "created_at", True), [])

    def test_get_rejects_a_consumed_invitation(self) -> None:
        code = create_user_invitation(self.open_registry, 100, 100)
        with self.open_registry() as unit_of_work:
            invitation = unit_of_work.user_invitation_repository.get_by_secret_hash(hashlib.sha256(code.encode("ascii")).digest())
            assert invitation is not None
            self.assertTrue(unit_of_work.user_invitation_repository.consume(invitation.uuid, 150))
            unit_of_work.commit()

        self.assertIsNone(get_available_user_invitation(self.open_registry, code, 160))

    def test_revoke_rejects_missing_and_consumed_invitations(self) -> None:
        self.assertFalse(revoke_user_invitation(self.open_registry, uuid4()))
        code = create_user_invitation(self.open_registry, 100, 100)
        with self.open_registry() as unit_of_work:
            invitation = unit_of_work.user_invitation_repository.get_by_secret_hash(hashlib.sha256(code.encode("ascii")).digest())
            assert invitation is not None
            self.assertTrue(unit_of_work.user_invitation_repository.consume(invitation.uuid, 150))
            unit_of_work.commit()

        self.assertFalse(revoke_user_invitation(self.open_registry, invitation.uuid))
        with self.open_registry() as unit_of_work:
            stored = unit_of_work.user_invitation_repository.get(invitation.uuid)
        assert stored is not None
        self.assertEqual(stored.consumed_at, 150)

    def test_list_returns_active_and_consumed_invitations(self) -> None:
        active_code = create_user_invitation(self.open_registry, 100, 100)
        consumed_code = create_user_invitation(self.open_registry, 100, 100)
        with self.open_registry() as unit_of_work:
            consumed = unit_of_work.user_invitation_repository.get_by_secret_hash(hashlib.sha256(consumed_code.encode("ascii")).digest())
            assert consumed is not None
            self.assertTrue(unit_of_work.user_invitation_repository.consume(consumed.uuid, 150))
            unit_of_work.commit()

        invitations = list_user_invitations(self.open_registry, "created_at", True)

        self.assertEqual(len(invitations), 2)
        by_hash = {invitation.secret_hash: invitation for invitation in invitations}
        active = by_hash[hashlib.sha256(active_code.encode("ascii")).digest()]
        self.assertIsNone(active.consumed_at)
        self.assertEqual(by_hash[hashlib.sha256(consumed_code.encode("ascii")).digest()].consumed_at, 150)
