import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

from app.application.registry.exceptions import InvitationNotAvailableError, UserNameUnavailableError
from app.application.registry.use_cases.register_user import register_user
from app.application.registry.use_cases.user_invitation import create_user_invitation, revoke_user_invitation
from app.domain.registry.model.user_invitation import UserInvitation
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.registry.repository.user import SqliteUserRepository
from app.infrastructure.persistence.sqlite.registry.unit_of_work import SqliteRegistryUnitOfWork
from tests.fakes import FakePasswordHasher


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"


class RegisterUserUseCaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.database = SqliteDatabase.initialize(Path(self.temporary_directory.name) / "registry.sqlite", SCHEMA_PATH)
        self.password_hasher = FakePasswordHasher()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def open_registry(self) -> SqliteRegistryUnitOfWork:
        return SqliteRegistryUnitOfWork(self.database)

    def create_invitation(self) -> UserInvitation:
        code = create_user_invitation(self.open_registry, 100, 100)
        with self.open_registry() as unit_of_work:
            invitation = unit_of_work.user_invitation_repository.get_by_secret_hash(hashlib.sha256(code.encode("ascii")).digest())
        assert invitation is not None
        return invitation

    def test_register_consumes_invitation_and_creates_user(self) -> None:
        invitation = self.create_invitation()

        user = register_user(self.open_registry, self.password_hasher, invitation.uuid, "Alice", "correct horse battery", 150)

        self.assertEqual(user.name, "Alice")
        self.assertEqual(user.normalized_name, "alice")
        self.assertEqual(user.password_hash, "$argon2id$test$correct horse battery")
        self.assertEqual(user.created_at, 150)
        self.assertEqual(user.password_changed_at, 150)
        self.assertEqual(self.password_hasher.passwords, ["correct horse battery"])
        with self.open_registry() as unit_of_work:
            stored_invitation = unit_of_work.user_invitation_repository.get(invitation.uuid)
            sessions = unit_of_work.auth_session_repository.list_by_user(user.uuid)
        assert stored_invitation is not None
        self.assertEqual(stored_invitation.consumed_at, 150)
        self.assertEqual(sessions, [])

    def test_consume_rejects_an_invalid_invitation(self) -> None:
        with self.assertRaises(InvitationNotAvailableError):
            register_user(self.open_registry, self.password_hasher, uuid4(), "Alice", "correct horse battery", 150)

        self.assertEqual(self.password_hasher.passwords, ["correct horse battery"])

    def test_consume_rejects_invitation_before_creation_and_at_expiration(self) -> None:
        invitation = self.create_invitation()

        for timestamp in (99, 200):
            with self.subTest(timestamp=timestamp):
                with self.assertRaises(InvitationNotAvailableError):
                    register_user(self.open_registry, self.password_hasher, invitation.uuid, f"Alice {timestamp}", "correct horse battery", timestamp)

        with self.open_registry() as unit_of_work:
            stored_invitation = unit_of_work.user_invitation_repository.get(invitation.uuid)
            self.assertEqual(unit_of_work.user_repository.list_all(), [])
        assert stored_invitation is not None
        self.assertIsNone(stored_invitation.consumed_at)

    def test_consume_rejects_a_deleted_invitation(self) -> None:
        invitation = self.create_invitation()
        self.assertTrue(revoke_user_invitation(self.open_registry, invitation.uuid))

        with self.assertRaises(InvitationNotAvailableError):
            register_user(self.open_registry, self.password_hasher, invitation.uuid, "Alice", "correct horse battery", 150)

        with self.open_registry() as unit_of_work:
            self.assertEqual(unit_of_work.user_repository.list_all(), [])

    def test_consumed_invitation_cannot_create_a_second_user(self) -> None:
        invitation = self.create_invitation()
        register_user(self.open_registry, self.password_hasher, invitation.uuid, "Alice", "correct horse battery", 150)

        with self.assertRaises(InvitationNotAvailableError):
            register_user(self.open_registry, self.password_hasher, invitation.uuid, "Bob", "another valid password", 160)

        with self.open_registry() as unit_of_work:
            users = unit_of_work.user_repository.list_all()
        self.assertEqual([user.name for user in users], ["Alice"])

    def test_password_hashing_failure_does_not_consume_invitation(self) -> None:
        invitation = self.create_invitation()

        with patch.object(self.password_hasher, "hash", side_effect=RuntimeError("hashing failed")):
            with self.assertRaisesRegex(RuntimeError, "hashing failed"):
                register_user(self.open_registry, self.password_hasher, invitation.uuid, "Alice", "correct horse battery", 150)

        with self.open_registry() as unit_of_work:
            stored_invitation = unit_of_work.user_invitation_repository.get(invitation.uuid)
            self.assertEqual(unit_of_work.user_repository.list_all(), [])
        assert stored_invitation is not None
        self.assertIsNone(stored_invitation.consumed_at)

    def test_existing_name_does_not_consume_invitation(self) -> None:
        first_invitation = self.create_invitation()
        register_user(self.open_registry, self.password_hasher, first_invitation.uuid, "Alice", "correct horse battery", 150)
        second_invitation = self.create_invitation()
        self.password_hasher.passwords.clear()

        with self.assertRaises(UserNameUnavailableError):
            register_user(self.open_registry, self.password_hasher, second_invitation.uuid, "  ＡLICE  ", "another valid password", 150)

        self.assertEqual(self.password_hasher.passwords, ["another valid password"])
        with self.open_registry() as unit_of_work:
            invitation = unit_of_work.user_invitation_repository.get(second_invitation.uuid)
        assert invitation is not None
        self.assertIsNone(invitation.consumed_at)

    @patch.object(SqliteUserRepository, "create", side_effect=RuntimeError("creation failed"))
    def test_user_creation_failure_rolls_back_invitation_consumption(self, create) -> None:
        invitation = self.create_invitation()

        with self.assertRaisesRegex(RuntimeError, "creation failed"):
            register_user(self.open_registry, self.password_hasher, invitation.uuid, "Alice", "another valid password", 150)

        with self.open_registry() as unit_of_work:
            stored_invitation = unit_of_work.user_invitation_repository.get(invitation.uuid)
            stored_user = unit_of_work.user_repository.get_by_normalized_name("alice")
        assert stored_invitation is not None
        self.assertIsNone(stored_invitation.consumed_at)
        self.assertIsNone(stored_user)
        create.assert_called_once()


if __name__ == "__main__":
    unittest.main()
