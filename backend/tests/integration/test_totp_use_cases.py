import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.application.registry.exceptions import InvalidCurrentPasswordError, InvalidTotpCodeError, InvalidTotpSetupError, TotpAlreadyEnabledError, TotpNotEnabledError
from app.application.registry.use_cases.authentication import login
from app.application.registry.use_cases.password import change_password
from app.application.registry.use_cases.totp import RECOVERY_CODE_COUNT, disable_totp, enable_totp, start_totp_setup
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

    def enable(self) -> list[str]:
        start_totp_setup(self.open_registry, self.password_hasher, self.totp_authenticator, self.user, "current password", 20)
        return enable_totp(self.open_registry, self.totp_authenticator, self.user, "123456", 20)

    def test_enabling_totp_persists_the_encrypted_secret_and_returns_new_recovery_codes(self) -> None:
        recovery_codes = self.enable()

        with self.open_registry() as unit_of_work:
            method = unit_of_work.mfa_method_repository.get_totp_by_user(self.user.uuid)
            stored_codes = unit_of_work.recovery_code_repository.list_by_user(self.user.uuid)
        assert method is not None
        self.assertEqual(method.secret_encrypted, b"FAKESECRET")
        self.assertEqual(method.confirmed_at, 20)
        self.assertEqual(len(recovery_codes), RECOVERY_CODE_COUNT)
        self.assertEqual(len(set(recovery_codes)), RECOVERY_CODE_COUNT)
        self.assertEqual(len(stored_codes), RECOVERY_CODE_COUNT)
        self.assertCountEqual([code.code_hash for code in stored_codes], [hashlib.sha256(code.encode("ascii")).digest() for code in recovery_codes])

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
        session_token, _ = login(self.open_registry, self.password_hasher, "Alice", "current password", False, 22, totp_authenticator=self.totp_authenticator)
        self.assertIsInstance(session_token, str)

    def test_enable_rejects_missing_setups_and_invalid_codes_without_confirming_totp(self) -> None:
        with self.assertRaises(InvalidTotpSetupError):
            enable_totp(self.open_registry, self.totp_authenticator, self.user, "123456", 20)

        start_totp_setup(self.open_registry, self.password_hasher, self.totp_authenticator, self.user, "current password", 20)
        with self.assertRaises(InvalidTotpCodeError):
            enable_totp(self.open_registry, self.totp_authenticator, self.user, "000000", 20)

        with self.open_registry() as unit_of_work:
            method = unit_of_work.mfa_method_repository.get_totp_by_user(self.user.uuid)
            self.assertEqual(unit_of_work.recovery_code_repository.list_by_user(self.user.uuid), [])
        assert method is not None
        self.assertIsNone(method.confirmed_at)

    @patch.object(SqliteMfaMethodRepository, "confirm", return_value=False)
    def test_enable_leaves_a_pending_setup_when_confirmation_loses_its_compare_and_set(self, confirm) -> None:
        start_totp_setup(self.open_registry, self.password_hasher, self.totp_authenticator, self.user, "current password", 20)

        with self.assertRaises(InvalidTotpSetupError):
            enable_totp(self.open_registry, self.totp_authenticator, self.user, "123456", 21)

        with self.open_registry() as unit_of_work:
            method = unit_of_work.mfa_method_repository.get_totp_by_user(self.user.uuid)
            recovery_codes = unit_of_work.recovery_code_repository.list_by_user(self.user.uuid)
        assert method is not None
        self.assertIsNone(method.confirmed_at)
        self.assertEqual(recovery_codes, [])
        confirm.assert_called_once()

    def test_login_and_password_change_require_totp_after_it_is_enabled(self) -> None:
        self.enable()

        with self.assertRaises(InvalidTotpCodeError):
            login(self.open_registry, self.password_hasher, "Alice", "current password", False, 30, totp_authenticator=self.totp_authenticator)
        session_token, _ = login(self.open_registry, self.password_hasher, "Alice", "current password", False, 30, totp_authenticator=self.totp_authenticator, totp_code="123456")
        self.assertIsInstance(session_token, str)

        with self.assertRaises(InvalidTotpCodeError):
            change_password(self.open_registry, self.password_hasher, self.user, "current password", "replacement password", 31, self.totp_authenticator)
        change_password(self.open_registry, self.password_hasher, self.user, "current password", "replacement password", 31, self.totp_authenticator, "123456")

    def test_disabling_totp_requires_a_valid_totp_code(self) -> None:
        self.enable()

        with self.assertRaises(InvalidTotpCodeError):
            disable_totp(self.open_registry, self.totp_authenticator, self.user, "000000", 30)
        disable_totp(self.open_registry, self.totp_authenticator, self.user, "123456", 30)

        with self.open_registry() as unit_of_work:
            self.assertIsNone(unit_of_work.mfa_method_repository.get_totp_by_user(self.user.uuid))
        with self.assertRaises(TotpNotEnabledError):
            disable_totp(self.open_registry, self.totp_authenticator, self.user, "123456", 31)


if __name__ == "__main__":
    unittest.main()
