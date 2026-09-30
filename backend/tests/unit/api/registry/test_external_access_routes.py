import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from uuid import UUID

from fastapi import HTTPException, Response

from app.api.registry.routes.external_access import create_ledger_external_access, list_ledger_external_accesses, revoke_ledger_external_access
from app.application.registry.exceptions import ExternalAccessLimitReachedError, InvalidCurrentPasswordError, InvalidTotpCodeError, LedgerGrantNotFoundError, LedgerNotFoundError, TotpCodeAlreadyUsedError, TotpRequiredError


class ExternalAccessRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger_uuid = UUID("00000000-0000-0000-0000-000000000001")
        self.grant_uuid = UUID("00000000-0000-0000-0000-000000000002")
        self.request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(databases=SimpleNamespace(open_registry=object()), password_hasher=object(), totp_authenticator=object())))
        self.user = SimpleNamespace(uuid=UUID("00000000-0000-0000-0000-000000000003"))

    def test_creation_translates_domain_errors(self) -> None:
        cases = (
            (LedgerNotFoundError, 404, "Ledger not found"),
            (ExternalAccessLimitReachedError, 409, "External access limit reached"),
            (TotpRequiredError, 401, "TOTP required"),
            (TotpCodeAlreadyUsedError, 409, "TOTP code already used"),
            (InvalidTotpCodeError, 401, "Invalid TOTP code"),
            (InvalidCurrentPasswordError, 401, "Invalid current password"),
        )
        payload = SimpleNamespace(name="Sync", current_password="password", totp_code=None)

        for error, status_code, detail in cases:
            with self.subTest(error=error), patch("app.api.registry.routes.external_access.execute_credential_operation", new=AsyncMock(side_effect=error)):
                with self.assertRaises(HTTPException) as raised:
                    asyncio.run(create_ledger_external_access(self.ledger_uuid, payload, Response(), self.request, self.user))

            self.assertEqual(raised.exception.status_code, status_code)
            self.assertEqual(raised.exception.detail, detail)

    def test_list_and_creation_return_external_access_details(self) -> None:
        grant = SimpleNamespace(uuid=self.grant_uuid, grantee_uuid=self.user.uuid, created_at=10)
        access = SimpleNamespace(uuid=self.user.uuid, name="Sync")
        with patch("app.api.registry.routes.external_access.list_external_access_grants_for_owned_ledger", return_value=[(grant, access)]):
            listed = list_ledger_external_accesses(self.ledger_uuid, self.request, self.user)
        self.assertEqual(listed[0].grant_uuid, self.grant_uuid)
        self.assertEqual(listed[0].name, "Sync")

        payload = SimpleNamespace(name="Sync", current_password="password", totp_code=None)
        response = Response()
        with patch("app.api.registry.routes.external_access.execute_credential_operation", new=AsyncMock(return_value=(grant, "secret"))):
            created = asyncio.run(create_ledger_external_access(self.ledger_uuid, payload, response, self.request, self.user))
        self.assertEqual(created.token, "secret")
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_listing_translates_an_unknown_ledger(self) -> None:
        with patch("app.api.registry.routes.external_access.list_external_access_grants_for_owned_ledger", side_effect=LedgerNotFoundError):
            with self.assertRaises(HTTPException) as raised:
                list_ledger_external_accesses(self.ledger_uuid, self.request, self.user)
        self.assertEqual((raised.exception.status_code, raised.exception.detail), (404, "Ledger not found"))

    def test_revocation_translates_domain_errors(self) -> None:
        cases = (
            (LedgerGrantNotFoundError, 404, "External access not found"),
            (TotpRequiredError, 401, "TOTP required"),
            (TotpCodeAlreadyUsedError, 409, "TOTP code already used"),
            (InvalidTotpCodeError, 401, "Invalid TOTP code"),
            (InvalidCurrentPasswordError, 401, "Invalid current password"),
        )
        payload = SimpleNamespace(current_password="password", totp_code=None)

        for error, status_code, detail in cases:
            with self.subTest(error=error), patch("app.api.registry.routes.external_access.execute_credential_operation", new=AsyncMock(side_effect=error)):
                with self.assertRaises(HTTPException) as raised:
                    asyncio.run(revoke_ledger_external_access(self.ledger_uuid, self.grant_uuid, payload, self.request, self.user))

            self.assertEqual(raised.exception.status_code, status_code)
            self.assertEqual(raised.exception.detail, detail)

    def test_revocation_completes_without_a_response_body(self) -> None:
        payload = SimpleNamespace(current_password="password", totp_code=None)
        operation = AsyncMock(return_value=None)
        with patch("app.api.registry.routes.external_access.execute_credential_operation", new=operation):
            result = asyncio.run(revoke_ledger_external_access(self.ledger_uuid, self.grant_uuid, payload, self.request, self.user))
        self.assertIsNone(result)
        operation.assert_awaited_once()
