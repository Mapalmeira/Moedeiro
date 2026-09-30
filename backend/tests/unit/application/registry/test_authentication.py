from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from app.application.registry.exceptions import InvalidSessionError
from app.application.registry.use_cases.authentication import resolve_session_user, update_session_activity


class AuthenticationUseCasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.uuid = uuid4()
        self.unit_of_work = MagicMock()
        self.factory = MagicMock()
        self.factory.return_value.__enter__.return_value = self.unit_of_work

    def test_session_resolution_rejects_a_user_deleted_concurrently(self) -> None:
        self.unit_of_work.auth_session_repository.get_active_by_token_hash.return_value = SimpleNamespace(uuid=self.uuid, user_uuid=self.uuid)
        self.unit_of_work.user_repository.get.return_value = None

        with self.assertRaises(InvalidSessionError):
            resolve_session_user(self.factory, "ascii-token", 10)

    def test_activity_update_rejects_a_session_revoked_concurrently(self) -> None:
        self.unit_of_work.auth_session_repository.update_last_activity.return_value = False

        with self.assertRaises(InvalidSessionError):
            update_session_activity(self.factory, self.uuid, 10)
