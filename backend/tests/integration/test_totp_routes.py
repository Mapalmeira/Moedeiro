from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest

from fastapi import HTTPException, Request, Response

from app.api.authentication import require_authenticated_user
from app.api.schema.totp import DisableTotpRequest, EnableTotpRequest, StartTotpSetupRequest
from app.api.totp import confirm_setup, disable, start_setup
from app.application.registry.exceptions import InvalidTotpCodeError
from app.application.registry.use_cases.authentication import login
from app.factory import create_app
from app.settings import Settings
from tests.fakes import FakePasswordHasher, FakeRateLimiter, FakeTotpAuthenticator


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
        )
        self.password_hasher = FakePasswordHasher()
        self.totp_authenticator = FakeTotpAuthenticator()
        self.application = create_app(settings, self.password_hasher, FakeRateLimiter(), self.totp_authenticator)
        with self.application.state.databases.open_registry() as unit_of_work:
            self.user = unit_of_work.user_repository.create("Alice", self.password_hasher.hash("current password"), 10)
            unit_of_work.commit()
        self.password_hasher.passwords.clear()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def request(self, totp_code: str | None = None) -> Request:
        token, _ = login(self.application.state.databases.open_registry, self.password_hasher, "Alice", "current password", False, int(time.time()), totp_authenticator=self.totp_authenticator, totp_code=totp_code)
        return Request({"type": "http", "app": self.application, "client": ("192.0.2.1", 50000), "headers": [(b"cookie", f"moedeiro_session={token}".encode("ascii"))]})

    def test_setup_then_enable_returns_recovery_codes_and_enables_totp(self) -> None:
        request = self.request()
        user = require_authenticated_user(request)

        setup = start_setup(StartTotpSetupRequest(current_password="current password"), request, user)
        result = confirm_setup(EnableTotpRequest(code="123456"), request, user)

        self.assertIn("otpauth://totp/Moedeiro:Alice", setup.provisioning_uri)
        self.assertEqual(len(result.recovery_codes), 10)
        with self.application.state.databases.open_registry() as unit_of_work:
            self.assertIsNotNone(unit_of_work.mfa_method_repository.get_totp_by_user(self.user.uuid))

    def test_enabled_totp_requires_a_code_to_login(self) -> None:
        request = self.request()
        user = require_authenticated_user(request)
        setup = start_setup(StartTotpSetupRequest(current_password="current password"), request, user)
        confirm_setup(EnableTotpRequest(code="123456"), request, user)

        with self.assertRaises(InvalidTotpCodeError):
            login(self.application.state.databases.open_registry, self.password_hasher, "Alice", "current password", False, int(time.time()), totp_authenticator=self.totp_authenticator)

    def test_disable_requires_the_current_totp_code(self) -> None:
        request = self.request()
        user = require_authenticated_user(request)
        setup = start_setup(StartTotpSetupRequest(current_password="current password"), request, user)
        confirm_setup(EnableTotpRequest(code="123456"), request, user)
        with self.assertRaises(HTTPException) as raised:
            disable(DisableTotpRequest(code="000000"), request, Response(), user)
        self.assertEqual(raised.exception.status_code, 401)
        response = Response()
        disable(DisableTotpRequest(code="123456"), request, response, user)
        self.assertEqual(sum(name == b"set-cookie" for name, _ in response.raw_headers), 2)

        with self.application.state.databases.open_registry() as unit_of_work:
            self.assertIsNone(unit_of_work.mfa_method_repository.get_totp_by_user(self.user.uuid))


if __name__ == "__main__":
    unittest.main()
