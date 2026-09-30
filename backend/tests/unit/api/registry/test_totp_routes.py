import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.api.registry.routes.totp import confirm_setup, remove_totp, start_setup
from app.application.registry.exceptions import InvalidCurrentPasswordError, InvalidTotpCodeError, InvalidTotpSetupError, TotpAlreadyEnabledError, TotpCodeAlreadyUsedError, TotpNotEnabledError


class TotpRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.request = SimpleNamespace(
            app=SimpleNamespace(
                state=SimpleNamespace(
                    databases=SimpleNamespace(open_registry=object()),
                    settings=SimpleNamespace(totp_setup_ip_attempts_rate_limit="5/minute"),
                    password_hasher=object(),
                    totp_authenticator=object(),
                )
            )
        )
        self.user = object()

    def test_setup_translates_invalid_password_and_existing_enrollment(self) -> None:
        payload = SimpleNamespace(current_password="password")
        cases = (
            (InvalidCurrentPasswordError, 401, "Invalid current password"),
            (TotpAlreadyEnabledError, 409, "TOTP already enabled"),
        )
        for error, status_code, detail in cases:
            with self.subTest(error=error), patch("app.api.registry.routes.totp.check_rate_limit"), patch("app.api.registry.routes.totp.execute_credential_operation", new=AsyncMock(side_effect=error)):
                with self.assertRaises(HTTPException) as raised:
                    asyncio.run(start_setup(payload, self.request, self.user))
            self.assertEqual(raised.exception.status_code, status_code)
            self.assertEqual(raised.exception.detail, detail)

    def test_confirmation_translates_setup_errors(self) -> None:
        payload = SimpleNamespace(code="123456")
        cases = (
            (InvalidTotpSetupError, 400, "Invalid or expired TOTP setup"),
            (InvalidTotpCodeError, 401, "Invalid TOTP code"),
            (TotpAlreadyEnabledError, 409, "TOTP already enabled"),
        )
        for error, status_code, detail in cases:
            with self.subTest(error=error), patch("app.api.registry.routes.totp.confirm_totp_setup", side_effect=error):
                with self.assertRaises(HTTPException) as raised:
                    confirm_setup(payload, self.request, self.user)
            self.assertEqual(raised.exception.status_code, status_code)
            self.assertEqual(raised.exception.detail, detail)

    def test_removal_translates_credential_and_enrollment_errors(self) -> None:
        payload = SimpleNamespace(current_password="password", code="123456")
        cases = (
            (TotpCodeAlreadyUsedError, 409, "TOTP code already used"),
            (InvalidCurrentPasswordError, 401, "Invalid current password"),
            (InvalidTotpCodeError, 401, "Invalid TOTP code"),
            (TotpNotEnabledError, 409, "TOTP not enabled"),
        )
        for error, status_code, detail in cases:
            with self.subTest(error=error), patch("app.api.registry.routes.totp.execute_credential_operation", new=AsyncMock(side_effect=error)):
                with self.assertRaises(HTTPException) as raised:
                    asyncio.run(remove_totp(payload, self.request, self.user))
            self.assertEqual(raised.exception.status_code, status_code)
            self.assertEqual(raised.exception.detail, detail)
