from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from app.application.registry.exceptions import InvalidTotpCodeError
from app.application.registry.use_cases.totp import verify_totp


class TotpUseCasesTest(unittest.TestCase):
    def test_verify_requires_an_authenticator_when_a_method_is_enabled(self) -> None:
        unit_of_work = MagicMock()
        unit_of_work.mfa_method_repository.get_totp_by_user.return_value = SimpleNamespace(confirmed_at=10)

        with self.assertRaises(InvalidTotpCodeError):
            verify_totp(unit_of_work, None, uuid4(), "123456", 20)
