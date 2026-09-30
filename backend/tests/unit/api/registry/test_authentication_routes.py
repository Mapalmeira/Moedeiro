from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.api.registry.routes.authentication import refresh


class AuthenticationRoutesTest(unittest.TestCase):
    def test_refresh_rejects_a_missing_remember_cookie(self) -> None:
        request = SimpleNamespace(
            cookies={},
            app=SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace(refresh_ip_attempts_rate_limit="1/minute"))),
        )
        with patch("app.api.registry.routes.authentication.check_rate_limit"):
            with self.assertRaises(HTTPException) as raised:
                refresh(request, SimpleNamespace())

        self.assertEqual((raised.exception.status_code, raised.exception.detail), (401, "Invalid session"))
