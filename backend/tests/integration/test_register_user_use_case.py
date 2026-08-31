import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

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

    def create_invitation(self):
        return create_user_invitation(self.open_registry, 100, 100)

    def get_invitation(self, code: str) -> UserInvitation | None:
        with self.open_registry() as unit_of_work:
            return unit_of_work.user_invitation_repository.get_by_secret_hash(hashlib.sha256(code.encode("ascii")).digest())

    def test_register_consumes_invitation_and_creates_user(self) -> None:
        code = self.create_invitation()

        user = register_user(self.open_registry, self.password_hasher, code, "Alice", "correct horse battery", 150)

        self.assertEqual(user.name, "Alice")
        self.assertEqual(user.normalized_name, "alice")
        self.assertEqual(user.password_hash, "$argon2id$test$correct horse battery")
        self.assertEqual(user.created_at, 150)
        self.assertEqual(user.password_changed_at, 150)
        self.assertEqual(self.password_hasher.passwords, ["correct horse battery"])
        with self.open_registry() as unit_of_work:
            invitation = unit_of_work.user_invitation_repository.get_by_secret_hash(hashlib.sha256(code.encode("ascii")).digest())
            sessions = unit_of_work.auth_session_repository.list_by_user(user.uuid)
        assert invitation is not None
        self.assertEqual(invitation.consumed_at, 150)
        self.assertEqual(sessions, [])

    def test_consume_rejects_an_invalid_invitation(self) -> None:
        with self.assertRaises(InvitationNotAvailableError):
            register_user(self.open_registry, self.password_hasher, "0" * 16, "Alice", "correct horse battery", 150)

        self.assertEqual(self.password_hasher.passwords, ["correct horse battery"])

    def test_consume_rejects_invitation_before_creation_and_at_expiration(self) -> None:
        code = self.create_invitation()

        for timestamp in (99, 200):
            with self.subTest(timestamp=timestamp):
                with self.assertRaises(InvitationNotAvailableError):
                    register_user(self.open_registry, self.password_hasher, code, f"Alice {timestamp}", "correct horse battery", timestamp)

        invitation = self.get_invitation(code)
        assert invitation is not None
        self.assertIsNone(invitation.consumed_at)
        with self.open_registry() as unit_of_work:
            self.assertEqual(unit_of_work.user_repository.list_all(), [])

    def test_consume_rejects_a_revoked_invitation(self) -> None:
        code = self.create_invitation()
        invitation = self.get_invitation(code)
        assert invitation is not None
        self.assertTrue(revoke_user_invitation(self.open_registry, invitation.uuid, 120))

        with self.assertRaises(InvitationNotAvailableError):
            register_user(self.open_registry, self.password_hasher, code, "Alice", "correct horse battery", 150)

        with self.open_registry() as unit_of_work:
            self.assertEqual(unit_of_work.user_repository.list_all(), [])

    def test_consumed_invitation_cannot_create_a_second_user(self) -> None:
        code = self.create_invitation()
        register_user(self.open_registry, self.password_hasher, code, "Alice", "correct horse battery", 150)

        with self.assertRaises(InvitationNotAvailableError):
            register_user(self.open_registry, self.password_hasher, code, "Bob", "another valid password", 160)

        with self.open_registry() as unit_of_work:
            users = unit_of_work.user_repository.list_all()
        self.assertEqual([user.name for user in users], ["Alice"])

    def test_password_hashing_failure_does_not_consume_invitation(self) -> None:
        code = self.create_invitation()

        with patch.object(self.password_hasher, "hash", side_effect=RuntimeError("hashing failed")):
            with self.assertRaisesRegex(RuntimeError, "hashing failed"):
                register_user(self.open_registry, self.password_hasher, code, "Alice", "correct horse battery", 150)

        invitation = self.get_invitation(code)
        assert invitation is not None
        self.assertIsNone(invitation.consumed_at)
        with self.open_registry() as unit_of_work:
            self.assertEqual(unit_of_work.user_repository.list_all(), [])

    def test_existing_name_does_not_consume_invitation(self) -> None:
        first_code = self.create_invitation()
        register_user(self.open_registry, self.password_hasher, first_code, "Alice", "correct horse battery", 150)
        second_code = self.create_invitation()
        second_invitation = self.get_invitation(second_code)
        assert second_invitation is not None
        self.password_hasher.passwords.clear()

        with self.assertRaises(UserNameUnavailableError):
            register_user(self.open_registry, self.password_hasher, second_code, "  ＡLICE  ", "another valid password", 150)

        self.assertEqual(self.password_hasher.passwords, ["another valid password"])
        with self.open_registry() as unit_of_work:
            invitation = unit_of_work.user_invitation_repository.get(second_invitation.uuid)
        assert invitation is not None
        self.assertIsNone(invitation.consumed_at)

    @patch.object(SqliteUserRepository, "create", side_effect=RuntimeError("creation failed"))
    def test_user_creation_failure_rolls_back_invitation_consumption(self, create) -> None:
        code = self.create_invitation()
        invitation = self.get_invitation(code)
        assert invitation is not None

        with self.assertRaisesRegex(RuntimeError, "creation failed"):
            register_user(self.open_registry, self.password_hasher, code, "Alice", "another valid password", 150)

        with self.open_registry() as unit_of_work:
            stored_invitation = unit_of_work.user_invitation_repository.get(invitation.uuid)
            stored_user = unit_of_work.user_repository.get_by_normalized_name("alice")
        assert stored_invitation is not None
        self.assertIsNone(stored_invitation.consumed_at)
        self.assertIsNone(stored_user)
        create.assert_called_once()


if __name__ == "__main__":
    unittest.main()
