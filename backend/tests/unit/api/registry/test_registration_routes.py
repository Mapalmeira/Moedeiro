import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.api.registry.routes.registration import create_user
from app.application.registry.exceptions import InvitationNotAvailableError


class RegistrationRoutesTest(unittest.TestCase):
    def test_creation_translates_a_concurrently_consumed_invitation(self) -> None:
        request = SimpleNamespace(
            app=SimpleNamespace(
                state=SimpleNamespace(
                    settings=SimpleNamespace(registration_ip_attempts_rate_limit="1/minute"),
                    databases=SimpleNamespace(open_registry=object()),
                )
            )
        )
        payload = SimpleNamespace(invitation_code="0" * 16, name="Alice", password="valid password")

        with patch("app.api.registry.routes.registration.check_rate_limit"), patch(
            "app.api.registry.routes.registration.execute_credential_operation",
            new=AsyncMock(side_effect=InvitationNotAvailableError),
        ):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(create_user(payload, request))

        self.assertEqual((raised.exception.status_code, raised.exception.detail), (404, "Invitation not available"))
