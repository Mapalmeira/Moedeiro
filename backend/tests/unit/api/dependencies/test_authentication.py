from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.api.dependencies.authentication import require_ledger_grantee
from app.application.registry.exceptions import ExternalAccessNotFoundError


class AuthenticationDependenciesTest(unittest.TestCase):
    def test_external_access_rejects_an_invalid_authorization_scheme(self) -> None:
        request = SimpleNamespace(headers={"Authorization": "Basic credentials"})

        with self.assertRaises(HTTPException) as raised:
            require_ledger_grantee(request, credentials=None)

        self.assertEqual(raised.exception.status_code, 401)
        self.assertEqual(raised.exception.detail, "Invalid external access token")
        self.assertEqual(raised.exception.headers, {"WWW-Authenticate": "Bearer"})

    def test_grantee_uses_session_without_authorization_and_rejects_unknown_bearer(self) -> None:
        anonymous_request = SimpleNamespace(headers={})
        user = object()
        with patch("app.api.dependencies.authentication.require_authenticated_user", return_value=user):
            self.assertIs(require_ledger_grantee(anonymous_request, None), user)

        request = SimpleNamespace(
            headers={"Authorization": "Bearer missing"},
            app=SimpleNamespace(state=SimpleNamespace(databases=SimpleNamespace(open_registry=object()))),
        )
        credentials = SimpleNamespace(scheme="Bearer", credentials="missing")
        with patch("app.api.dependencies.authentication.resolve_external_access", side_effect=ExternalAccessNotFoundError):
            with self.assertRaises(HTTPException) as raised:
                require_ledger_grantee(request, credentials)

        self.assertEqual((raised.exception.status_code, raised.exception.detail), (401, "Invalid external access token"))
