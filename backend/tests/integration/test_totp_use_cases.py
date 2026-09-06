from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.application.registry.exceptions import InvalidCurrentPasswordError, InvalidTotpCodeError, InvalidTotpSetupError, TotpAlreadyEnabledError, TotpCodeAlreadyUsedError, TotpNotEnabledError, TotpRequiredError
from app.application.registry.use_cases.authentication import login
from app.application.registry.use_cases.mfa import disable_mfa
from app.application.registry.use_cases.password import change_password
from app.application.registry.use_cases.totp import confirm_totp_setup, disable_totp, get_totp_status, start_totp_setup
from app.domain.registry.model.mfa_method import TOTP_SETUP_TTL_SECONDS
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.registry.repository.mfa_method import SqliteMfaMethodRepository
from app.infrastructure.persistence.sqlite.registry.unit_of_work import SqliteRegistryUnitOfWork
from tests.fakes import FakePasswordHasher, FakeTotpAuthenticator


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"


class TotpUseCasesTest(unittest.TestCase):
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

    def enable(self) -> None:
        start_totp_setup(self.open_registry, self.password_hasher, self.totp_authenticator, self.user, "current password", 20)
        confirm_totp_setup(self.open_registry, self.totp_authenticator, self.user, "123456", 20)

    def is_totp_enabled(self) -> bool:
        return get_totp_status(self.open_registry, self.totp_authenticator, self.user, 20).state == "ENABLED"

    def test_totp_status_is_false_without_a_confirmed_method_and_true_after_confirmation(self) -> None:
        self.assertFalse(self.is_totp_enabled())

        start_totp_setup(self.open_registry, self.password_hasher, self.totp_authenticator, self.user, "current password", 20)
        self.assertFalse(self.is_totp_enabled())

        confirm_totp_setup(self.open_registry, self.totp_authenticator, self.user, "123456", 20)
        self.assertTrue(self.is_totp_enabled())

    def test_enabling_totp_persists_the_encrypted_secret_without_creating_recovery_codes(self) -> None:
        self.enable()

        with self.open_registry() as unit_of_work:
            method = unit_of_work.mfa_method_repository.get_totp_by_user(self.user.uuid)
            stored_codes = unit_of_work.recovery_code_repository.list_by_user(self.user.uuid)
        assert method is not None
        self.assertEqual(method.secret_encrypted, b"FAKESECRET")
        self.assertEqual(method.confirmed_at, 20)
        self.assertEqual(stored_codes, [])

    def test_setup_requires_the_current_password_and_can_only_be_enabled_once(self) -> None:
        with self.assertRaises(InvalidCurrentPasswordError):
            start_totp_setup(self.open_registry, self.password_hasher, self.totp_authenticator, self.user, "wrong password", 20)

        self.enable()
        with self.assertRaises(TotpAlreadyEnabledError):
            start_totp_setup(self.open_registry, self.password_hasher, self.totp_authenticator, self.user, "current password", 21)

    def test_starting_again_replaces_a_pending_setup_without_enabling_totp(self) -> None:
        start_totp_setup(self.open_registry, self.password_hasher, self.totp_authenticator, self.user, "current password", 20)
        with self.open_registry() as unit_of_work:
            first = unit_of_work.mfa_method_repository.get_totp_by_user(self.user.uuid)
        start_totp_setup(self.open_registry, self.password_hasher, self.totp_authenticator, self.user, "current password", 21)
        with self.open_registry() as unit_of_work:
            second = unit_of_work.mfa_method_repository.get_totp_by_user(self.user.uuid)
        assert first is not None
        assert second is not None
        self.assertNotEqual(second.uuid, first.uuid)
        self.assertIsNone(second.confirmed_at)
        result = login(self.open_registry, self.password_hasher, "Alice", "current password", False, 22, totp_authenticator=self.totp_authenticator)
        assert result is not None
        session_token, _ = result
        self.assertIsInstance(session_token, str)

    def test_enable_rejects_missing_setups_and_invalid_codes_without_confirming_totp(self) -> None:
        with self.assertRaises(InvalidTotpSetupError):
            confirm_totp_setup(self.open_registry, self.totp_authenticator, self.user, "123456", 20)

        start_totp_setup(self.open_registry, self.password_hasher, self.totp_authenticator, self.user, "current password", 20)
        with self.assertRaises(InvalidTotpCodeError):
            confirm_totp_setup(self.open_registry, self.totp_authenticator, self.user, "000000", 20)

        with self.open_registry() as unit_of_work:
            method = unit_of_work.mfa_method_repository.get_totp_by_user(self.user.uuid)
            self.assertEqual(unit_of_work.recovery_code_repository.list_by_user(self.user.uuid), [])
        assert method is not None
        self.assertIsNone(method.confirmed_at)

    @patch.object(SqliteMfaMethodRepository, "confirm", return_value=False)
    def test_enable_leaves_a_pending_setup_when_confirmation_loses_its_compare_and_set(self, confirm) -> None:
        start_totp_setup(self.open_registry, self.password_hasher, self.totp_authenticator, self.user, "current password", 20)

        with self.assertRaises(InvalidTotpSetupError):
            confirm_totp_setup(self.open_registry, self.totp_authenticator, self.user, "123456", 21)

        with self.open_registry() as unit_of_work:
            method = unit_of_work.mfa_method_repository.get_totp_by_user(self.user.uuid)
            recovery_codes = unit_of_work.recovery_code_repository.list_by_user(self.user.uuid)
        assert method is not None
        self.assertIsNone(method.confirmed_at)
        self.assertEqual(recovery_codes, [])
        confirm.assert_called_once()

    def test_pending_setup_can_be_confirmed_just_before_expiration(self) -> None:
        start_totp_setup(self.open_registry, self.password_hasher, self.totp_authenticator, self.user, "current password", 20)
        confirm_totp_setup(self.open_registry, self.totp_authenticator, self.user, "123456", 20 + TOTP_SETUP_TTL_SECONDS - 1)
        self.assertTrue(self.is_totp_enabled())

    def test_setup_persists_the_pending_expiration(self) -> None:
        status = start_totp_setup(self.open_registry, self.password_hasher, self.totp_authenticator, self.user, "current password", 20)

        self.assertEqual(status.expires_at, 20 + TOTP_SETUP_TTL_SECONDS)
        with self.open_registry() as unit_of_work:
            self.assertEqual(unit_of_work.mfa_method_repository.get_totp_by_user(self.user.uuid).expires_unconfirmed_at, status.expires_at)

    def test_expired_setup_is_rejected_without_decrypting_or_verifying_the_secret(self) -> None:
        for elapsed in (TOTP_SETUP_TTL_SECONDS, TOTP_SETUP_TTL_SECONDS + 1):
            with self.subTest(elapsed=elapsed):
                start_totp_setup(self.open_registry, self.password_hasher, self.totp_authenticator, self.user, "current password", 20)
                with patch.object(self.totp_authenticator, "decrypt_secret") as decrypt:
                    with self.assertRaises(InvalidTotpSetupError):
                        confirm_totp_setup(self.open_registry, self.totp_authenticator, self.user, "123456", 20 + elapsed)
                    decrypt.assert_not_called()
                with self.open_registry() as unit_of_work:
                    self.assertIsNotNone(unit_of_work.mfa_method_repository.get_totp_by_user(self.user.uuid))

    def test_restart_after_expiration_gets_a_fresh_confirmation_window(self) -> None:
        start_totp_setup(self.open_registry, self.password_hasher, self.totp_authenticator, self.user, "current password", 20)
        restarted_at = 20 + TOTP_SETUP_TTL_SECONDS
        start_totp_setup(self.open_registry, self.password_hasher, self.totp_authenticator, self.user, "current password", restarted_at)
        confirm_totp_setup(self.open_registry, self.totp_authenticator, self.user, "123456", restarted_at + 1)
        self.assertTrue(self.is_totp_enabled())

    def test_confirmed_setup_does_not_expire(self) -> None:
        self.enable()
        with self.assertRaises(TotpAlreadyEnabledError):
            confirm_totp_setup(self.open_registry, self.totp_authenticator, self.user, "123456", 20 + TOTP_SETUP_TTL_SECONDS)
        self.assertTrue(self.is_totp_enabled())

    def test_confirmation_before_creation_is_rejected_without_deleting_setup(self) -> None:
        start_totp_setup(self.open_registry, self.password_hasher, self.totp_authenticator, self.user, "current password", 20)
        with self.assertRaises(InvalidTotpSetupError):
            confirm_totp_setup(self.open_registry, self.totp_authenticator, self.user, "123456", 19)
        with self.open_registry() as unit_of_work:
            self.assertIsNotNone(unit_of_work.mfa_method_repository.get_totp_by_user(self.user.uuid))

    def test_login_and_password_change_require_totp_after_it_is_enabled(self) -> None:
        self.enable()

        with self.assertRaises(TotpRequiredError):
            login(self.open_registry, self.password_hasher, "Alice", "current password", False, 30, totp_authenticator=self.totp_authenticator)
        result = login(self.open_registry, self.password_hasher, "Alice", "current password", False, 30, totp_authenticator=self.totp_authenticator, totp_code="123456")
        assert result is not None
        session_token, _ = result
        self.assertIsInstance(session_token, str)

        with self.assertRaises(TotpRequiredError):
            change_password(self.open_registry, self.password_hasher, self.user, "current password", "replacement password", 31, self.totp_authenticator)
        change_password(self.open_registry, self.password_hasher, self.user, "current password", "replacement password", 60, self.totp_authenticator, "123456")

    def test_rejects_reusing_a_totp_counter(self) -> None:
        self.enable()
        self.totp_authenticator.fixed_counter = 7

        login(self.open_registry, self.password_hasher, "Alice", "current password", False, 30, totp_authenticator=self.totp_authenticator, totp_code="123456")

        with self.assertRaises(TotpCodeAlreadyUsedError):
            login(self.open_registry, self.password_hasher, "Alice", "current password", False, 31, totp_authenticator=self.totp_authenticator, totp_code="123456")

    def test_user_can_disable_totp_with_the_current_password_and_totp_code_without_ending_sessions(self) -> None:
        self.enable()
        login(self.open_registry, self.password_hasher, "Alice", "current password", True, 30, totp_authenticator=self.totp_authenticator, totp_code="123456")

        disable_totp(self.open_registry, self.password_hasher, self.totp_authenticator, self.user, "current password", "123456", 60)

        with self.open_registry() as unit_of_work:
            self.assertIsNone(unit_of_work.mfa_method_repository.get_totp_by_user(self.user.uuid))
            self.assertEqual(len(unit_of_work.auth_session_repository.list_by_user(self.user.uuid)), 1)
            self.assertEqual(len(unit_of_work.remember_session_repository.list_by_user(self.user.uuid)), 1)

    def test_user_mfa_disable_rejects_invalid_credentials_and_missing_totp(self) -> None:
        with self.assertRaises(TotpNotEnabledError):
            disable_totp(self.open_registry, self.password_hasher, self.totp_authenticator, self.user, "current password", "123456", 20)

        self.enable()
        with self.assertRaises(InvalidCurrentPasswordError):
            disable_totp(self.open_registry, self.password_hasher, self.totp_authenticator, self.user, "wrong password", "123456", 21)
        with self.assertRaises(InvalidTotpCodeError):
            disable_totp(self.open_registry, self.password_hasher, self.totp_authenticator, self.user, "current password", "000000", 21)

        with self.open_registry() as unit_of_work:
            self.assertIsNotNone(unit_of_work.mfa_method_repository.get_totp_by_user(self.user.uuid))

    def test_admin_mfa_disable_removes_totp_and_sessions(self) -> None:
        self.enable()
        login(self.open_registry, self.password_hasher, "Alice", "current password", True, 30, totp_authenticator=self.totp_authenticator, totp_code="123456")

        self.assertEqual(disable_mfa(self.open_registry, self.user.uuid), 1)

        with self.open_registry() as unit_of_work:
            self.assertIsNone(unit_of_work.mfa_method_repository.get_totp_by_user(self.user.uuid))
            self.assertEqual(unit_of_work.auth_session_repository.list_by_user(self.user.uuid), [])
            self.assertEqual(unit_of_work.remember_session_repository.list_by_user(self.user.uuid), [])
        self.assertEqual(disable_mfa(self.open_registry, self.user.uuid), 0)


if __name__ == "__main__":
    unittest.main()
