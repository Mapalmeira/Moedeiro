from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest

from fastapi import HTTPException, Request, Response
from pydantic import ValidationError

from app.api.authentication import require_authenticated_user
from app.api.password import change_current_password, recover_password
from app.api.schema.password import ChangePasswordRequest, ResetPasswordRequest
from app.application.registry.use_cases.authentication import login
from app.application.registry.use_cases.password import create_recovery_code
from app.factory import create_app
from app.settings import Settings
from tests.fakes import FakePasswordHasher, FakeRateLimiter, FakeTotpAuthenticator


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class PasswordRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        directory = Path(self.temporary_directory.name)
        settings = Settings(
            registry_schema_path=REGISTRY_SCHEMA_PATH,
            ledger_schema_path=LEDGER_SCHEMA_PATH,
            registry_db_path=directory / "registry/registry.sqlite",
            ledger_dbs_dir=directory / "ledgers",
            password_recovery_attempts_rate_limit="3/hour",
            password_hash_concurrency=2,
        )
        self.password_hasher = FakePasswordHasher()
        self.rate_limiter = FakeRateLimiter()
        self.application = create_app(settings, self.password_hasher, self.rate_limiter, FakeTotpAuthenticator())
        with self.application.state.databases.open_registry() as unit_of_work:
            self.user = unit_of_work.user_repository.create("Alice", self.password_hasher.hash("current password"), 10)
            unit_of_work.commit()
        self.password_hasher.passwords.clear()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def request(self, cookies: dict[str, str] | None = None, ip: str = "192.0.2.1") -> Request:
        headers = []
        if cookies:
            headers.append((b"cookie", "; ".join(f"{name}={value}" for name, value in cookies.items()).encode("ascii")))
        return Request({"type": "http", "app": self.application, "client": (ip, 50000), "headers": headers})

    @staticmethod
    def cookie_headers(response: Response) -> list[str]:
        return [value.decode("latin-1") for name, value in response.raw_headers if name == b"set-cookie"]

    def session_request(self) -> Request:
        result = login(self.application.state.databases.open_registry, self.password_hasher, "Alice", "current password", False, int(time.time()))
        assert result is not None
        token, _ = result
        return self.request({"moedeiro_session": token})

    def enable_totp(self) -> None:
        with self.application.state.databases.open_registry() as unit_of_work:
            unit_of_work.mfa_method_repository.create(self.user.uuid, "TOTP", b"FAKESECRET", 10, 10)
            unit_of_work.commit()

    def test_change_requires_an_authenticated_short_session(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            require_authenticated_user(self.request())

        self.assertEqual(raised.exception.status_code, 401)

    def test_change_updates_password_deletes_sessions_and_clears_cookies(self) -> None:
        request = self.session_request()
        response = Response(status_code=204)

        change_current_password(ChangePasswordRequest(current_password="current password", new_password="replacement password"), request, response, require_authenticated_user(request))

        self.assertEqual(sum("Max-Age=0" in header for header in self.cookie_headers(response)), 2)
        with self.application.state.databases.open_registry() as unit_of_work:
            user = unit_of_work.user_repository.get(self.user.uuid)
            sessions = unit_of_work.auth_session_repository.list_by_user(self.user.uuid)
        assert user is not None
        self.assertEqual(user.password_hash, "$argon2id$test$replacement password")
        self.assertEqual(sessions, [])

    def test_change_requests_totp_then_accepts_the_repeated_request(self) -> None:
        request = self.session_request()
        self.enable_totp()

        with self.assertRaises(HTTPException) as raised:
            change_current_password(ChangePasswordRequest(current_password="current password", new_password="replacement password"), request, Response(), require_authenticated_user(request))
        self.assertEqual(raised.exception.detail, "TOTP required")

        change_current_password(ChangePasswordRequest(current_password="current password", new_password="replacement password", totp_code="123456"), request, Response(), require_authenticated_user(request))

    def test_change_rejects_an_invalid_current_password_without_clearing_cookies(self) -> None:
        request = self.session_request()
        response = Response(status_code=204)

        with self.assertRaises(HTTPException) as raised:
            change_current_password(ChangePasswordRequest(current_password="incorrect password", new_password="replacement password"), request, response, require_authenticated_user(request))

        self.assertEqual(raised.exception.status_code, 401)
        self.assertEqual(self.cookie_headers(response), [])

    def test_change_checks_hashing_capacity_after_session_authentication(self) -> None:
        request = self.session_request()
        semaphore = self.application.state.password_hash_semaphore
        for _ in range(self.application.state.settings.password_hash_concurrency):
            self.assertTrue(semaphore.acquire(blocking=False))
        try:
            with self.assertRaises(HTTPException) as raised:
                change_current_password(ChangePasswordRequest(current_password="current password", new_password="replacement password"), request, Response(), require_authenticated_user(request))
        finally:
            for _ in range(self.application.state.settings.password_hash_concurrency):
                semaphore.release()

        self.assertEqual(raised.exception.status_code, 503)

    def test_recovery_resets_password_consumes_the_code_and_clears_cookies(self) -> None:
        code = create_recovery_code(self.application.state.databases.open_registry, self.user.uuid, 20)
        response = Response(status_code=204)

        recover_password(ResetPasswordRequest(name="Alice", recovery_code=code, new_password="replacement password"), self.request(), response)

        self.assertEqual(sum("Max-Age=0" in header for header in self.cookie_headers(response)), 2)
        self.assertEqual(self.rate_limiter.checks, [("3/hour", "password-recovery-attempts", "192.0.2.1")])
        with self.application.state.databases.open_registry() as unit_of_work:
            user = unit_of_work.user_repository.get(self.user.uuid)
            codes = unit_of_work.recovery_code_repository.list_by_user(self.user.uuid)
        assert user is not None
        self.assertEqual(user.password_hash, "$argon2id$test$replacement password")
        self.assertIsNotNone(codes[0].used_at)

    def test_recovery_returns_one_opaque_error_for_unknown_user_wrong_and_consumed_codes(self) -> None:
        code = create_recovery_code(self.application.state.databases.open_registry, self.user.uuid, 20)
        recover_password(ResetPasswordRequest(name="Alice", recovery_code=code, new_password="replacement password"), self.request(), Response())
        self.password_hasher.passwords.clear()

        for name, candidate in (("Unknown", code), ("Alice", "0" * 32), ("Alice", code)):
            with self.subTest(name=name, candidate=candidate):
                with self.assertRaises(HTTPException) as raised:
                    recover_password(ResetPasswordRequest(name=name, recovery_code=candidate, new_password="another password"), self.request(), Response())
                self.assertEqual(raised.exception.status_code, 401)
                self.assertEqual(raised.exception.detail, "Invalid credentials")
        self.assertEqual(self.password_hasher.passwords, [])

    def test_recovery_rate_limit_precedes_lookup_and_hashing(self) -> None:
        code = create_recovery_code(self.application.state.databases.open_registry, self.user.uuid, 20)
        self.rate_limiter.rejected_namespace = "password-recovery-attempts"

        with self.assertRaises(HTTPException) as raised:
            recover_password(ResetPasswordRequest(name="Alice", recovery_code=code, new_password="replacement password"), self.request(), Response())

        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(self.password_hasher.passwords, [])

    def test_password_request_models_reject_short_passwords_and_malformed_codes(self) -> None:
        with self.assertRaises(ValidationError):
            ChangePasswordRequest(current_password="current password", new_password="short")
        with self.assertRaises(ValidationError):
            ResetPasswordRequest(name="Alice", recovery_code="invalid", new_password="replacement password")

    def test_password_routes_expose_the_expected_response_shapes(self) -> None:
        paths = self.application.openapi()["paths"]

        for path in ("/api/password/change", "/api/password/recovery"):
            with self.subTest(path=path):
                self.assertNotIn("content", paths[path]["post"]["responses"]["204"])
        self.assertNotIn("/api/password/recovery-code", paths)
        self.assertNotIn("/api/password/recovery/validate", paths)


if __name__ == "__main__":
    unittest.main()
