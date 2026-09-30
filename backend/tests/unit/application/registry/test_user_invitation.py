from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from app.application.registry.use_cases.user_invitation import revoke_user_invitation


class UserInvitationUseCasesTest(unittest.TestCase):
    def test_revocation_returns_false_when_the_invitation_is_deleted_concurrently(self) -> None:
        unit_of_work = MagicMock()
        unit_of_work.user_invitation_repository.get.return_value = SimpleNamespace(consumed_at=None)
        unit_of_work.user_invitation_repository.delete.return_value = False
        factory = MagicMock()
        factory.return_value.__enter__.return_value = unit_of_work

        self.assertFalse(revoke_user_invitation(factory, uuid4()))
