import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest

from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from app.api.dependencies.authentication import require_authenticated_user
from app.api.registry.routes.totp import confirm_setup, get_totp_status, remove_totp, start_setup
from app.api.registry.schema.totp import ConfirmTotpRequest, DisableTotpRequest, StartTotpSetupRequest
from app.application.registry.exceptions import TotpRequiredError
from app.application.registry.use_cases.authentication import login
from app.factory import create_app
from app.settings import Settings
from tests.fakes import FakeCredentialOperationExecutor, FakePasswordHasher, FakeRateLimiter, FakeTotpAuthenticator


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class TotpRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        directory = Path(self.temporary_directory.name)
        settings = Settings(
            registry_schema_path=REGISTRY_SCHEMA_PATH,
            ledger_schema_path=LEDGER_SCHEMA_PATH,
            registry_db_path=directory / "registry/registry.sqlite",
            ledger_dbs_dir=directory / "ledgers",
            totp_setup_ip_attempts_rate_limit="2/hour",
            authenticated_user_operations_rate_limit="7/minute",
        )
        self.password_hasher = FakePasswordHasher()
        self.totp_authenticator = FakeTotpAuthenticator()
        self.rate_limiter = FakeRateLimiter()
        self.application = create_app(settings, self.password_hasher, self.rate_limiter, self.totp_authenticator, FakeCredentialOperationExecutor(), mount_frontend=False)
        with self.application.state.databases.open_registry() as unit_of_work:
            self.user = unit_of_work.user_repository.create("Alice", self.password_hasher.hash("current password"), 10)
            unit_of_work.commit()
        self.password_hasher.passwords.clear()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def request(self, totp_code: str | None = None) -> Request:
        result = login(self.application.state.databases.open_registry, self.password_hasher, "Alice", "current password", False, int(time.time()), totp_authenticator=self.totp_authenticator, totp_code=totp_code)
        assert result is not None
        token, _ = result
        return Request({"type": "http", "app": self.application, "client": ("192.0.2.1", 50000), "headers": [(b"cookie", f"moedeiro_session={token}".encode("ascii"))]})

    def test_get_status_reports_disabled_before_confirmation_and_enabled_after_confirmation(self) -> None:
        request = self.request()
        user = require_authenticated_user(request)

        self.assertFalse(get_totp_status(request, user).enabled)
        setup = asyncio.run(start_setup(StartTotpSetupRequest(current_password="current password"), request, user))
        pending_status = get_totp_status(request, user)
        self.assertFalse(pending_status.enabled)
        self.assertGreaterEqual(setup.setup_expires_at, int(time.time()) + 599)
        self.assertLessEqual(setup.setup_expires_at, int(time.time()) + 600)
        confirm_setup(ConfirmTotpRequest(code="123456"), request, user)
        enabled_status = get_totp_status(request, user)
        self.assertTrue(enabled_status.enabled)

    def test_get_status_route_is_exposed_and_requires_authentication(self) -> None:
        operation = self.application.openapi()["paths"]["/api/totp"]["get"]

        self.assertIn("200", operation["responses"])
        with TestClient(self.application) as client:
            response = client.get("/api/totp")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Invalid session"})

    def test_setup_then_enable_confirms_totp_without_creating_recovery_codes(self) -> None:
        request = self.request()
        user = require_authenticated_user(request)

        setup = asyncio.run(start_setup(StartTotpSetupRequest(current_password="current password"), request, user))
        result = confirm_setup(ConfirmTotpRequest(code="123456"), request, user)

        self.assertIn("otpauth://totp/Moedeiro:Alice", setup.provisioning_uri)
        self.assertIsNone(result)
        self.assertEqual(self.rate_limiter.checks, [("7/minute", "authenticated-user-operations", str(self.user.uuid)), ("2/hour", "totp-setup-ip-attempts", "192.0.2.1")])
        with self.application.state.databases.open_registry() as unit_of_work:
            self.assertIsNotNone(unit_of_work.mfa_method_repository.get_totp_by_user(self.user.uuid))
            self.assertEqual(unit_of_work.recovery_code_repository.list_by_user(self.user.uuid), [])

    def test_enabled_totp_requires_a_code_to_login(self) -> None:
        request = self.request()
        user = require_authenticated_user(request)
        asyncio.run(start_setup(StartTotpSetupRequest(current_password="current password"), request, user))
        confirm_setup(ConfirmTotpRequest(code="123456"), request, user)

        with self.assertRaises(TotpRequiredError):
            login(self.application.state.databases.open_registry, self.password_hasher, "Alice", "current password", False, int(time.time()), totp_authenticator=self.totp_authenticator)

    def test_setup_rate_limit_precedes_password_verification(self) -> None:
        request = self.request()
        user = require_authenticated_user(request)
        self.rate_limiter.rejected_namespace = "totp-setup-ip-attempts"

        with self.assertRaises(HTTPException) as raised:
            asyncio.run(start_setup(StartTotpSetupRequest(current_password="current password"), request, user))

        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(self.password_hasher.verifications, [("$argon2id$test$current password", "current password")])

    def test_authenticated_user_can_disable_totp_without_ending_the_current_session(self) -> None:
        setup_request = self.request()
        user = require_authenticated_user(setup_request)
        asyncio.run(start_setup(StartTotpSetupRequest(current_password="current password"), setup_request, user))
        confirm_setup(ConfirmTotpRequest(code="123456"), setup_request, user)
        request = self.request("123456")
        with self.application.state.databases.open_registry() as unit_of_work:
            session_count = len(unit_of_work.auth_session_repository.list_by_user(self.user.uuid))
        asyncio.run(remove_totp(DisableTotpRequest(current_password="current password", code="123456"), request, user))

        with self.application.state.databases.open_registry() as unit_of_work:
            self.assertIsNone(unit_of_work.mfa_method_repository.get_totp_by_user(self.user.uuid))
            self.assertEqual(len(unit_of_work.auth_session_repository.list_by_user(self.user.uuid)), session_count)

    def test_totp_disable_reports_when_the_totp_code_was_already_used(self) -> None:
        setup_request = self.request()
        user = require_authenticated_user(setup_request)
        asyncio.run(start_setup(StartTotpSetupRequest(current_password="current password"), setup_request, user))
        confirm_setup(ConfirmTotpRequest(code="123456"), setup_request, user)
        self.totp_authenticator.fixed_counter = 7
        request = self.request("123456")

        with self.assertRaises(HTTPException) as raised:
            asyncio.run(remove_totp(DisableTotpRequest(current_password="current password", code="123456"), request, user))

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, "TOTP code already used")

    def test_totp_disable_identifies_the_invalid_credential(self) -> None:
        setup_request = self.request()
        user = require_authenticated_user(setup_request)
        asyncio.run(start_setup(StartTotpSetupRequest(current_password="current password"), setup_request, user))
        confirm_setup(ConfirmTotpRequest(code="123456"), setup_request, user)
        request = self.request("123456")

        for current_password, code, detail in (
            ("wrong password", "123456", "Invalid current password"),
            ("current password", "000000", "Invalid TOTP code"),
        ):
            with self.subTest(current_password=current_password, code=code):
                with self.assertRaises(HTTPException) as raised:
                    asyncio.run(remove_totp(DisableTotpRequest(current_password=current_password, code=code), request, user))
                self.assertEqual(raised.exception.status_code, 401)
                self.assertEqual(raised.exception.detail, detail)


if __name__ == "__main__":
    unittest.main()
