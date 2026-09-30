from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.api.dependencies.authentication import require_ledger_grantee
from app.api.dependencies.pagination import validate_requested_page, validate_page_size
from app.application.registry.exceptions import ExternalAccessNotFoundError


class ApiDependenciesTest(unittest.TestCase):
    def test_requested_page_rejects_page_numbers_before_one(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            validate_requested_page(SimpleNamespace(), page_number=0, page_size=1)

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(raised.exception.detail, "page_number must be greater than or equal to 1")

    def test_page_size_rejects_values_before_one_and_above_the_configured_limit(self) -> None:
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace(max_page_size=20))))

        for page_size, detail in (
            (0, "page_size must be greater than or equal to 1"),
            (21, "page_size must be less than or equal to 20"),
        ):
            with self.subTest(page_size=page_size), self.assertRaises(HTTPException) as raised:
                validate_page_size(request, page_size)

            self.assertEqual(raised.exception.status_code, 422)
            self.assertEqual(raised.exception.detail, detail)

        with self.assertRaises(HTTPException) as raised:
            validate_requested_page(request, page_number=1, page_size=0)

        self.assertEqual(raised.exception.detail, "page_size must be greater than or equal to 1")

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
