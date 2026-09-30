from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException

from app.api.registry.routes.ledger import create_owned_ledger
from app.application.registry.exceptions import UserNotFoundError


class LedgerRoutesTest(unittest.TestCase):
    def test_creation_rejects_a_deleted_authenticated_user(self) -> None:
        databases = SimpleNamespace(open_registry=object(), initialize_ledger=object(), delete_ledger_database=object())
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(databases=databases)))
        payload = SimpleNamespace(name="Ledger", icon="lucide:BookOpen", color_code="#808080")
        user = SimpleNamespace(uuid=uuid4())

        with patch("app.api.registry.routes.ledger.create_ledger", side_effect=UserNotFoundError):
            with self.assertRaises(HTTPException) as raised:
                create_owned_ledger(payload, request, user)

        self.assertEqual((raised.exception.status_code, raised.exception.detail), (401, "Invalid session"))
