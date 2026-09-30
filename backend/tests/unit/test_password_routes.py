import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException, Response

from app.api.registry.routes.password import change_current_password, recover_password
from app.application.registry.exceptions import InvalidCurrentPasswordError, InvalidTotpCodeError, PasswordUpdateConflictError, RecoveryCodeNotAvailableError, TotpCodeAlreadyUsedError, TotpRequiredError, UserNotFoundError


class PasswordRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.request = SimpleNamespace(
            app=SimpleNamespace(
                state=SimpleNamespace(
                    databases=SimpleNamespace(open_registry=object()),
                    settings=SimpleNamespace(password_recovery_ip_attempts_rate_limit="10/hour", allow_insecure_http=False),
                    password_hasher=object(),
                    totp_authenticator=object(),
                )
            )
        )

    def test_change_translates_credential_errors(self) -> None:
        payload = SimpleNamespace(current_password="current", new_password="new", totp_code=None)
        cases = (
            (TotpRequiredError, 401, "TOTP required"),
            (TotpCodeAlreadyUsedError, 409, "TOTP code already used"),
            (InvalidTotpCodeError, 401, "Invalid TOTP code"),
            (InvalidCurrentPasswordError, 401, "Invalid current password"),
            (UserNotFoundError, 401, "Invalid session"),
            (PasswordUpdateConflictError, 409, "Password update conflict"),
        )
        for error, status_code, detail in cases:
            with self.subTest(error=error), patch("app.api.registry.routes.password.execute_credential_operation", new=AsyncMock(side_effect=error)):
                with self.assertRaises(HTTPException) as raised:
                    asyncio.run(change_current_password(payload, self.request, Response(), object()))
            self.assertEqual(raised.exception.status_code, status_code)
            self.assertEqual(raised.exception.detail, detail)

    def test_recovery_translates_credential_errors(self) -> None:
        payload = SimpleNamespace(name="alice", recovery_code="CODE", new_password="new", totp_code=None)
        cases = (
            (TotpRequiredError, 401, "TOTP required"),
            (TotpCodeAlreadyUsedError, 409, "TOTP code already used"),
            (InvalidTotpCodeError, 401, "Invalid TOTP code"),
            (UserNotFoundError, 401, "Invalid credentials"),
            (RecoveryCodeNotAvailableError, 401, "Invalid credentials"),
            (PasswordUpdateConflictError, 409, "Password update conflict"),
        )
        for error, status_code, detail in cases:
            with self.subTest(error=error), patch("app.api.registry.routes.password.check_rate_limit"), patch("app.api.registry.routes.password.execute_credential_operation", new=AsyncMock(side_effect=error)):
                with self.assertRaises(HTTPException) as raised:
                    asyncio.run(recover_password(payload, self.request, Response()))
            self.assertEqual(raised.exception.status_code, status_code)
            self.assertEqual(raised.exception.detail, detail)
