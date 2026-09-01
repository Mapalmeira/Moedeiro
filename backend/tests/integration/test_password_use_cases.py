import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.application.registry.exceptions import InvalidCurrentPasswordError, RecoveryCodeNotAvailableError, UserNotFoundError
from app.application.registry.use_cases.password import change_password, create_recovery_code, get_available_recovery_code, reset_password
from app.domain.registry.model.auth_session import DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, DEFAULT_INACTIVITY_TIMEOUT_SECONDS
from app.domain.registry.model.remember_session import DEFAULT_EXPIRATION_TIMEOUT_SECONDS
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.registry.repository.user import SqliteUserRepository
from app.infrastructure.persistence.sqlite.registry.unit_of_work import SqliteRegistryUnitOfWork
from tests.fakes import FakePasswordHasher


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"


class PasswordUseCasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.database = SqliteDatabase.initialize(Path(self.temporary_directory.name) / "registry.sqlite", SCHEMA_PATH)
        self.password_hasher = FakePasswordHasher()
        with self.open_registry() as unit_of_work:
            self.user = unit_of_work.user_repository.create("Alice", self.password_hasher.hash("current password"), 10)
            unit_of_work.commit()
        self.password_hasher.passwords.clear()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def open_registry(self) -> SqliteRegistryUnitOfWork:
        return SqliteRegistryUnitOfWork(self.database)

    def create_sessions(self) -> None:
        with self.open_registry() as unit_of_work:
            unit_of_work.auth_session_repository.create(self.user.uuid, b"s" * 32, 11, 11 + DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, DEFAULT_INACTIVITY_TIMEOUT_SECONDS)
            unit_of_work.remember_session_repository.create(self.user.uuid, b"r" * 32, 11, 11 + DEFAULT_EXPIRATION_TIMEOUT_SECONDS)
            unit_of_work.commit()

    def test_change_password_updates_the_hash_and_revokes_every_session(self) -> None:
        self.create_sessions()

        change_password(self.open_registry, self.password_hasher, self.user, "current password", "replacement password", 20)

        with self.open_registry() as unit_of_work:
            user = unit_of_work.user_repository.get(self.user.uuid)
            auth_sessions = unit_of_work.auth_session_repository.list_by_user(self.user.uuid)
            remember_sessions = unit_of_work.remember_session_repository.list_by_user(self.user.uuid)
        assert user is not None
        self.assertEqual(user.password_hash, "$argon2id$test$replacement password")
        self.assertEqual(user.password_changed_at, 20)
        self.assertEqual([session.revoked_at for session in auth_sessions], [20])
        self.assertEqual([session.revoked_at for session in remember_sessions], [20])

    def test_change_password_rejects_an_invalid_current_password_without_changes(self) -> None:
        self.create_sessions()

        with self.assertRaises(InvalidCurrentPasswordError):
            change_password(self.open_registry, self.password_hasher, self.user, "wrong current password", "replacement password", 20)

        with self.open_registry() as unit_of_work:
            user = unit_of_work.user_repository.get(self.user.uuid)
            auth_sessions = unit_of_work.auth_session_repository.list_by_user(self.user.uuid)
        assert user is not None
        self.assertEqual(user.password_hash, "$argon2id$test$current password")
        self.assertEqual(self.password_hasher.passwords, [])
        self.assertIsNone(auth_sessions[0].revoked_at)

    @patch.object(SqliteUserRepository, "update_password", return_value=False)
    def test_change_password_rolls_back_session_revocation_when_the_compare_and_set_fails(self, update_password) -> None:
        self.create_sessions()

        with self.assertRaises(InvalidCurrentPasswordError):
            change_password(self.open_registry, self.password_hasher, self.user, "current password", "replacement password", 20)

        with self.open_registry() as unit_of_work:
            auth_sessions = unit_of_work.auth_session_repository.list_by_user(self.user.uuid)
        self.assertIsNone(auth_sessions[0].revoked_at)
        update_password.assert_called_once()

    @patch("app.domain.registry.model.crockford_code.secrets.token_bytes", return_value=bytes(range(10)))
    def test_create_recovery_code_returns_a_crockford_code_and_persists_only_its_hash(self, token_bytes) -> None:
        code = create_recovery_code(self.open_registry, self.user.uuid, 20)

        with self.open_registry() as unit_of_work:
            recovery_code = unit_of_work.recovery_code_repository.get_by_code_hash(hashlib.sha256(code.encode("ascii")).digest())
        self.assertEqual(code, "000G40R40M30E209")
        assert recovery_code is not None
        self.assertEqual(recovery_code.user_uuid, self.user.uuid)
        self.assertEqual(recovery_code.created_at, 20)
        self.assertIsNone(recovery_code.used_at)

    def test_create_recovery_code_rejects_an_unknown_user(self) -> None:
        from uuid import uuid4

        with self.assertRaises(UserNotFoundError):
            create_recovery_code(self.open_registry, uuid4(), 20)

    def test_available_recovery_code_rejects_future_used_and_revoked_codes(self) -> None:
        code = create_recovery_code(self.open_registry, self.user.uuid, 20)

        self.assertIsNone(get_available_recovery_code(self.open_registry, code, 19))
        available = get_available_recovery_code(self.open_registry, code, 20)
        self.assertIsNotNone(available)
        assert available is not None
        with self.open_registry() as unit_of_work:
            unit_of_work.recovery_code_repository.revoke(available.uuid, 21)
            unit_of_work.commit()
        self.assertIsNone(get_available_recovery_code(self.open_registry, code, 22))

    def test_reset_password_consumes_the_code_and_revokes_every_session(self) -> None:
        code = create_recovery_code(self.open_registry, self.user.uuid, 20)
        remaining_code = create_recovery_code(self.open_registry, self.user.uuid, 21)
        self.create_sessions()

        reset_password(self.open_registry, self.password_hasher, code, "replacement password", 30)

        with self.open_registry() as unit_of_work:
            user = unit_of_work.user_repository.get(self.user.uuid)
            recovery_code = unit_of_work.recovery_code_repository.get_by_code_hash(hashlib.sha256(code.encode("ascii")).digest())
            remaining_recovery_code = unit_of_work.recovery_code_repository.get_by_code_hash(hashlib.sha256(remaining_code.encode("ascii")).digest())
            auth_sessions = unit_of_work.auth_session_repository.list_by_user(self.user.uuid)
            remember_sessions = unit_of_work.remember_session_repository.list_by_user(self.user.uuid)
        assert user is not None
        assert recovery_code is not None
        assert remaining_recovery_code is not None
        self.assertEqual(user.password_hash, "$argon2id$test$replacement password")
        self.assertEqual(user.password_changed_at, 30)
        self.assertEqual(recovery_code.used_at, 30)
        self.assertIsNone(remaining_recovery_code.revoked_at)
        self.assertEqual([session.revoked_at for session in auth_sessions], [30])
        self.assertEqual([session.revoked_at for session in remember_sessions], [30])
        with self.assertRaises(RecoveryCodeNotAvailableError):
            reset_password(self.open_registry, self.password_hasher, code, "another password", 31)

    @patch.object(SqliteUserRepository, "update_password", return_value=False)
    def test_reset_password_rolls_back_code_consumption_when_the_password_update_fails(self, update_password) -> None:
        code = create_recovery_code(self.open_registry, self.user.uuid, 20)

        with self.assertRaises(RecoveryCodeNotAvailableError):
            reset_password(self.open_registry, self.password_hasher, code, "replacement password", 30)

        with self.open_registry() as unit_of_work:
            recovery_code = unit_of_work.recovery_code_repository.get_by_code_hash(hashlib.sha256(code.encode("ascii")).digest())
        assert recovery_code is not None
        self.assertIsNone(recovery_code.used_at)
        update_password.assert_called_once()


if __name__ == "__main__":
    unittest.main()
