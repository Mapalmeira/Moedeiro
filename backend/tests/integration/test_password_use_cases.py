import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

from app.application.registry.exceptions import InvalidCurrentPasswordError, InvalidTotpCodeError, PasswordUpdateConflictError, RecoveryCodeNotAvailableError, TotpRequiredError, UserNotFoundError
from app.application.registry.use_cases.password import change_password, create_recovery_code, recover_password
from app.domain.registry.model.auth_session import DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, DEFAULT_INACTIVITY_TIMEOUT_SECONDS
from app.domain.registry.model.remember_session import DEFAULT_EXPIRATION_TIMEOUT_SECONDS
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.registry.repository.user import SqliteUserRepository
from app.infrastructure.persistence.sqlite.registry.unit_of_work import SqliteRegistryUnitOfWork
from tests.fakes import FakePasswordHasher, FakeTotpAuthenticator


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"


class PasswordUseCasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.database = SqliteDatabase.initialize(Path(self.temporary_directory.name) / "registry.sqlite", SCHEMA_PATH)
        self.password_hasher = FakePasswordHasher()
        self.totp_authenticator = FakeTotpAuthenticator()
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

    def enable_totp(self) -> None:
        with self.open_registry() as unit_of_work:
            unit_of_work.mfa_method_repository.create(self.user.uuid, "TOTP", b"FAKESECRET", 10, 10)
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
        self.assertEqual(auth_sessions, [])
        self.assertEqual(remember_sessions, [])

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
        self.assertEqual(len(auth_sessions), 1)

    def test_change_password_reports_when_the_authenticated_user_no_longer_exists(self) -> None:
        with self.open_registry() as unit_of_work:
            unit_of_work.user_repository.delete(self.user.uuid)
            unit_of_work.commit()

        with self.assertRaises(UserNotFoundError):
            change_password(self.open_registry, self.password_hasher, self.user, "current password", "replacement password", 20)

    def test_change_password_distinguishes_missing_and_invalid_totp(self) -> None:
        self.enable_totp()

        with self.assertRaises(TotpRequiredError):
            change_password(self.open_registry, self.password_hasher, self.user, "current password", "replacement password", 20, self.totp_authenticator)
        with self.assertRaises(InvalidTotpCodeError):
            change_password(self.open_registry, self.password_hasher, self.user, "current password", "replacement password", 20, self.totp_authenticator, "000000")

        with self.open_registry() as unit_of_work:
            user = unit_of_work.user_repository.get(self.user.uuid)
        assert user is not None
        self.assertEqual(user.password_hash, "$argon2id$test$current password")

    @patch.object(SqliteUserRepository, "update_password", return_value=False)
    def test_change_password_leaves_sessions_unchanged_when_compare_and_set_fails(self, update_password) -> None:
        self.create_sessions()

        with self.assertRaises(PasswordUpdateConflictError):
            change_password(self.open_registry, self.password_hasher, self.user, "current password", "replacement password", 20)

        with self.open_registry() as unit_of_work:
            self.assertEqual(len(unit_of_work.auth_session_repository.list_by_user(self.user.uuid)), 1)
        update_password.assert_called_once()

    @patch("app.domain.registry.model.crockford_code.secrets.token_bytes", return_value=bytes(range(10)))
    def test_create_recovery_code_returns_80_random_bits_and_persists_only_the_hash(self, token_bytes) -> None:
        code = create_recovery_code(self.open_registry, self.user.uuid, 20)

        with self.open_registry() as unit_of_work:
            recovery_code = unit_of_work.recovery_code_repository.get_active_by_user(self.user.uuid, 20)
        assert recovery_code is not None
        self.assertEqual(len(code), 16)
        self.assertEqual(recovery_code.code_hash, hashlib.sha256(code.encode("ascii")).digest())
        self.assertEqual(recovery_code.created_at, 20)
        self.assertEqual(recovery_code.expires_at, 3_620)
        token_bytes.assert_called_once_with(10)

    def test_create_recovery_code_replaces_the_previous_active_code(self) -> None:
        create_recovery_code(self.open_registry, self.user.uuid, 20)
        with self.open_registry() as unit_of_work:
            first = unit_of_work.recovery_code_repository.get_active_by_user(self.user.uuid, 20)
        assert first is not None

        create_recovery_code(self.open_registry, self.user.uuid, 21)

        with self.open_registry() as unit_of_work:
            second = unit_of_work.recovery_code_repository.get_active_by_user(self.user.uuid, 21)
            all_codes = unit_of_work.recovery_code_repository.list_by_user(self.user.uuid)
        assert second is not None
        self.assertNotEqual(second.uuid, first.uuid)
        self.assertEqual(all_codes, [second])

    def test_create_recovery_code_preserves_used_history(self) -> None:
        create_recovery_code(self.open_registry, self.user.uuid, 20)
        with self.open_registry() as unit_of_work:
            first = unit_of_work.recovery_code_repository.get_active_by_user(self.user.uuid, 20)
            assert first is not None
            unit_of_work.recovery_code_repository.consume(first.uuid, 21)
            unit_of_work.commit()

        create_recovery_code(self.open_registry, self.user.uuid, 22)

        with self.open_registry() as unit_of_work:
            codes = unit_of_work.recovery_code_repository.list_by_user(self.user.uuid)
        self.assertEqual(len(codes), 2)
        self.assertEqual(next(code for code in codes if code.uuid == first.uuid).used_at, 21)

    def test_create_recovery_code_rejects_an_unknown_user(self) -> None:
        with self.assertRaises(UserNotFoundError):
            create_recovery_code(self.open_registry, uuid4(), 20)

    def test_create_recovery_code_rejects_a_nonpositive_expiration(self) -> None:
        for expiration_seconds in (0, -1):
            with self.subTest(expiration_seconds=expiration_seconds):
                with self.assertRaises(ValueError):
                    create_recovery_code(self.open_registry, self.user.uuid, 20, expiration_seconds)

    def test_recover_password_rejects_an_expired_code(self) -> None:
        code = create_recovery_code(self.open_registry, self.user.uuid, 20, 10)

        with self.assertRaises(RecoveryCodeNotAvailableError):
            recover_password(self.open_registry, self.password_hasher, self.totp_authenticator, "Alice", code, "replacement password", None, 30)

    def test_recover_password_consumes_the_code_and_deletes_every_session(self) -> None:
        code = create_recovery_code(self.open_registry, self.user.uuid, 20)
        self.create_sessions()

        recover_password(self.open_registry, self.password_hasher, self.totp_authenticator, "Alice", code, "replacement password", None, 30)

        with self.open_registry() as unit_of_work:
            user = unit_of_work.user_repository.get(self.user.uuid)
            codes = unit_of_work.recovery_code_repository.list_by_user(self.user.uuid)
            auth_sessions = unit_of_work.auth_session_repository.list_by_user(self.user.uuid)
            remember_sessions = unit_of_work.remember_session_repository.list_by_user(self.user.uuid)
        assert user is not None
        self.assertEqual(user.password_hash, "$argon2id$test$replacement password")
        self.assertEqual(codes[0].used_at, 30)
        self.assertEqual(auth_sessions, [])
        self.assertEqual(remember_sessions, [])
        with self.assertRaises(RecoveryCodeNotAvailableError):
            recover_password(self.open_registry, self.password_hasher, self.totp_authenticator, "Alice", code, "another password", None, 31)

    def test_recover_password_requires_totp_when_enabled(self) -> None:
        code = create_recovery_code(self.open_registry, self.user.uuid, 20)
        self.enable_totp()

        with self.assertRaises(TotpRequiredError):
            recover_password(self.open_registry, self.password_hasher, self.totp_authenticator, "Alice", code, "replacement password", None, 30)
        with self.assertRaises(InvalidTotpCodeError):
            recover_password(self.open_registry, self.password_hasher, self.totp_authenticator, "Alice", code, "replacement password", "000000", 30)

        recover_password(self.open_registry, self.password_hasher, self.totp_authenticator, "Alice", code, "replacement password", "123456", 30)

    def test_recover_password_distinguishes_an_unknown_user_from_an_unavailable_code(self) -> None:
        code = create_recovery_code(self.open_registry, self.user.uuid, 20)
        self.password_hasher.passwords.clear()

        with self.assertRaises(UserNotFoundError):
            recover_password(self.open_registry, self.password_hasher, self.totp_authenticator, "Unknown", code, "replacement password", None, 30)
        with self.assertRaises(RecoveryCodeNotAvailableError):
            recover_password(self.open_registry, self.password_hasher, self.totp_authenticator, "Alice", "0" * 16, "replacement password", None, 30)

        self.assertEqual(self.password_hasher.passwords, [])

    @patch.object(SqliteUserRepository, "update_password", return_value=False)
    def test_recover_password_rolls_back_code_consumption_when_password_update_fails(self, update_password) -> None:
        code = create_recovery_code(self.open_registry, self.user.uuid, 20)

        with self.assertRaises(PasswordUpdateConflictError):
            recover_password(self.open_registry, self.password_hasher, self.totp_authenticator, "Alice", code, "replacement password", None, 30)

        with self.open_registry() as unit_of_work:
            recovery_code = unit_of_work.recovery_code_repository.get_active_by_user(self.user.uuid, 30)
        self.assertIsNotNone(recovery_code)
        update_password.assert_called_once()


if __name__ == "__main__":
    unittest.main()
