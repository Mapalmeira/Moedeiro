from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from app.application.ledger.exceptions import LedgerNotFoundError
from app.application.ledger.use_cases.ledger import access_granted_ledger, create_ledger, get_owned_ledger
from app.application.registry.exceptions import InvalidSessionError, InvalidTotpCodeError, RecoveryCodeNotAvailableError, UserNameUnavailableError, UserNotFoundError
from app.application.registry.secret import hash_ascii_secret
from app.application.registry.use_cases.authentication import resolve_session_user, update_session_activity
from app.application.registry.use_cases.mfa import disable_mfa
from app.application.registry.use_cases.password import recover_password
from app.application.registry.use_cases.totp import verify_totp
from app.application.registry.use_cases.user import create_user
from app.application.registry.use_cases.user_invitation import revoke_user_invitation


class UseCaseRaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.uuid = uuid4()
        self.unit_of_work = MagicMock()
        self.factory = MagicMock()
        self.factory.return_value.__enter__.return_value = self.unit_of_work

    def test_mfa_and_user_creation_reject_unknown_or_duplicate_users(self) -> None:
        self.unit_of_work.user_repository.get.return_value = None
        with self.assertRaises(UserNotFoundError):
            disable_mfa(self.factory, self.uuid)

        self.unit_of_work.user_repository.get_by_normalized_name.return_value = object()
        with self.assertRaises(UserNameUnavailableError):
            create_user(self.factory, MagicMock(hash=MagicMock(return_value="hash")), "Alice", "valid password", 10)

    def test_session_rejects_a_deleted_user_and_failed_activity_update(self) -> None:
        self.unit_of_work.auth_session_repository.get_active_by_token_hash.return_value = SimpleNamespace(uuid=self.uuid, user_uuid=self.uuid)
        self.unit_of_work.user_repository.get.return_value = None
        with self.assertRaises(InvalidSessionError):
            resolve_session_user(self.factory, "ascii-token", 10)

        self.unit_of_work.auth_session_repository.update_last_activity.return_value = False
        with self.assertRaises(InvalidSessionError):
            update_session_activity(self.factory, self.uuid, 10)

    def test_password_recovery_rejects_a_code_consumed_concurrently(self) -> None:
        code = "0123456789"
        user = SimpleNamespace(uuid=self.uuid, password_hash="old")
        self.unit_of_work.user_repository.get_by_normalized_name.return_value = user
        self.unit_of_work.recovery_code_repository.get_active_by_user.return_value = SimpleNamespace(
            uuid=self.uuid,
            code_hash=hash_ascii_secret(code),
        )
        self.unit_of_work.recovery_code_repository.consume.return_value = False
        self.unit_of_work.mfa_method_repository.get_totp_by_user.return_value = None

        with self.assertRaises(RecoveryCodeNotAvailableError):
            recover_password(self.factory, MagicMock(hash=MagicMock(return_value="new")), MagicMock(), "Alice", code, "new password", None, 10)

    def test_totp_requires_an_authenticator_when_a_method_is_enabled(self) -> None:
        self.unit_of_work.mfa_method_repository.get_totp_by_user.return_value = SimpleNamespace(confirmed_at=10)

        with self.assertRaises(InvalidTotpCodeError):
            verify_totp(self.unit_of_work, None, self.uuid, "123456", 20)

    def test_invitation_revocation_handles_a_concurrent_deletion(self) -> None:
        self.unit_of_work.user_invitation_repository.get.return_value = SimpleNamespace(consumed_at=None)
        self.unit_of_work.user_invitation_repository.delete.return_value = False

        self.assertFalse(revoke_user_invitation(self.factory, self.uuid))

    def test_ledger_use_cases_reject_missing_relations(self) -> None:
        self.unit_of_work.user_repository.get.return_value = None
        with self.assertRaises(UserNotFoundError):
            create_ledger(self.factory, MagicMock(), MagicMock(), self.uuid, "Ledger", "lucide:BookOpen", b"\x80\x80\x80", 10)

        self.unit_of_work.ledger_grant_repository.get_active_by_grantee_and_ledger.return_value = SimpleNamespace(role="OWNER")
        self.unit_of_work.ledger_repository.get.return_value = None
        with self.assertRaises(LedgerNotFoundError):
            access_granted_ledger(self.factory, self.uuid, self.uuid, 10)

        self.unit_of_work.ledger_grant_repository.get_active_owner_by_ledger.return_value = SimpleNamespace(grantee_uuid=self.uuid)
        with self.assertRaises(LedgerNotFoundError):
            get_owned_ledger(self.factory, self.uuid, self.uuid)
