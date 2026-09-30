import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from app.application.registry.exceptions import UserNotFoundError
from app.application.registry.use_cases.mfa import disable_mfa


class MfaUseCasesTest(unittest.TestCase):
    def test_disable_rejects_a_user_deleted_concurrently(self) -> None:
        unit_of_work = MagicMock()
        unit_of_work.user_repository.get.return_value = None
        factory = MagicMock()
        factory.return_value.__enter__.return_value = unit_of_work

        with self.assertRaises(UserNotFoundError):
            disable_mfa(factory, uuid4())
