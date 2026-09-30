from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from app.application.registry.exceptions import RecoveryCodeNotAvailableError
from app.application.registry.secret import hash_ascii_secret
from app.application.registry.use_cases.password import recover_password


class PasswordUseCasesTest(unittest.TestCase):
    def test_recovery_rejects_a_code_consumed_concurrently(self) -> None:
        user_uuid = uuid4()
        code = "0123456789"
        unit_of_work = MagicMock()
        unit_of_work.user_repository.get_by_normalized_name.return_value = SimpleNamespace(uuid=user_uuid, password_hash="old")
        unit_of_work.recovery_code_repository.get_active_by_user.return_value = SimpleNamespace(
            uuid=user_uuid,
            code_hash=hash_ascii_secret(code),
        )
        unit_of_work.recovery_code_repository.consume.return_value = False
        unit_of_work.mfa_method_repository.get_totp_by_user.return_value = None
        factory = MagicMock()
        factory.return_value.__enter__.return_value = unit_of_work

        with self.assertRaises(RecoveryCodeNotAvailableError):
            recover_password(factory, MagicMock(hash=MagicMock(return_value="new")), MagicMock(), "Alice", code, "new password", None, 10)
