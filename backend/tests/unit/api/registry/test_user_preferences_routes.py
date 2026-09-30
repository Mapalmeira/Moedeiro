from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException

from app.api.registry.routes.user_preferences import save_preferences
from app.application.registry.exceptions import UserNotFoundError


class UserPreferencesRoutesTest(unittest.TestCase):
    def test_save_rejects_a_deleted_user(self) -> None:
        payload = SimpleNamespace(language="pt-BR", theme="SYSTEM")
        user = SimpleNamespace(uuid=uuid4())
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(databases=SimpleNamespace(open_registry=object()))))

        with patch("app.api.registry.routes.user_preferences.save_user_preferences", side_effect=UserNotFoundError):
            with self.assertRaises(HTTPException) as raised:
                save_preferences(payload, request, user)

        self.assertEqual((raised.exception.status_code, raised.exception.detail), (401, "Invalid session"))
