from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi import HTTPException, Request, Response

from app.api.authentication import login_user, logout_user, refresh, validate_session
from app.api.schema.authentication import LoginRequest
from app.factory import create_app
from app.settings import Settings
from tests.fakes import FakePasswordHasher, FakeRateLimiter, FakeTotpAuthenticator


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class AuthenticationRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        directory = Path(self.temporary_directory.name)
        settings = Settings(
            registry_schema_path=REGISTRY_SCHEMA_PATH,
            ledger_schema_path=LEDGER_SCHEMA_PATH,
            registry_db_path=directory / "registry/registry.sqlite",
            ledger_dbs_dir=directory / "ledgers",
            login_ip_attempts_rate_limit="3/minute",
            password_hash_concurrency=2,
        )
        self.password_hasher = FakePasswordHasher()
        self.rate_limiter = FakeRateLimiter()
        self.application = create_app(settings, self.password_hasher, self.rate_limiter, FakeTotpAuthenticator())
        with self.application.state.databases.open_registry() as unit_of_work:
            self.user = unit_of_work.user_repository.create("Alice", self.password_hasher.hash("correct password"), 10)
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

    @staticmethod
    def cookie_value(headers: list[str], name: str) -> str:
        prefix = f"{name}="
        return next(header[len(prefix):].split(";", 1)[0] for header in headers if header.startswith(prefix))

    def test_login_sets_a_nonpersistent_short_cookie_and_a_30_day_remember_cookie(self) -> None:
        response = Response(status_code=204)

        login_user(LoginRequest(name="Alice", password="correct password", remember=True), self.request(), response)

        headers = self.cookie_headers(response)
        session_header = next(header for header in headers if header.startswith("moedeiro_session="))
        remember_header = next(header for header in headers if header.startswith("moedeiro_remember="))
        self.assertIn("HttpOnly", session_header)
        self.assertIn("Path=/api", session_header)
        self.assertIn("SameSite=strict", session_header)
        self.assertIn("Secure", session_header)
        self.assertNotIn("Max-Age", session_header)
        self.assertIn("Max-Age=2592000", remember_header)
        self.assertIn("Path=/api/authentication", remember_header)
        self.assertNotIn("Domain=", "".join(headers))
        self.assertEqual(self.rate_limiter.checks, [("3/minute", "login-ip-attempts", "192.0.2.1")])

    def test_login_without_remember_expires_any_client_remember_cookie(self) -> None:
        remembered_response = Response(status_code=204)
        login_user(LoginRequest(name="Alice", password="correct password", remember=True), self.request(), remembered_response)
        remembered_headers = self.cookie_headers(remembered_response)
        old_session = self.cookie_value(remembered_headers, "moedeiro_session")
        old_remember = self.cookie_value(remembered_headers, "moedeiro_remember")
        response = Response(status_code=204)

        login_user(LoginRequest(name="Alice", password="correct password"), self.request({"moedeiro_session": old_session, "moedeiro_remember": old_remember}), response)

        remember_header = next(header for header in self.cookie_headers(response) if header.startswith("moedeiro_remember="))
        self.assertIn("Max-Age=0", remember_header)
        with self.application.state.databases.open_registry() as unit_of_work:
            remember_sessions = unit_of_work.remember_session_repository.list_by_user(self.user.uuid)
        self.assertEqual(remember_sessions, [])

    def test_login_returns_one_generic_error_for_unknown_user_and_wrong_password(self) -> None:
        for name, password in (("Unknown", "correct password"), ("Alice", "wrong password")):
            with self.subTest(name=name, password=password):
                with self.assertRaises(HTTPException) as raised:
                    login_user(LoginRequest(name=name, password=password), self.request(), Response())
                self.assertEqual(raised.exception.status_code, 401)
                self.assertEqual(raised.exception.detail, "Invalid credentials")

    def test_login_requests_totp_then_accepts_the_same_credentials_with_the_code(self) -> None:
        with self.application.state.databases.open_registry() as unit_of_work:
            unit_of_work.mfa_method_repository.create(self.user.uuid, "TOTP", b"FAKESECRET", 10, 10)
            unit_of_work.commit()

        with self.assertRaises(HTTPException) as raised:
            login_user(LoginRequest(name="Alice", password="correct password"), self.request(), Response())
        self.assertEqual(raised.exception.detail, "TOTP required")

        response = Response(status_code=204)
        login_user(LoginRequest(name="Alice", password="correct password", totp_code="123456"), self.request(), response)
        self.assertTrue(any(header.startswith("moedeiro_session=") for header in self.cookie_headers(response)))

    def test_login_does_not_distinguish_an_invalid_totp_from_other_invalid_credentials(self) -> None:
        with self.application.state.databases.open_registry() as unit_of_work:
            unit_of_work.mfa_method_repository.create(self.user.uuid, "TOTP", b"FAKESECRET", 10, 10)
            unit_of_work.commit()

        with self.assertRaises(HTTPException) as raised:
            login_user(LoginRequest(name="Alice", password="correct password", totp_code="000000"), self.request(), Response())

        self.assertEqual(raised.exception.status_code, 401)
        self.assertEqual(raised.exception.detail, "Invalid credentials")

    def test_login_rate_limit_is_checked_before_password_verification(self) -> None:
        self.rate_limiter.rejected_namespace = "login-ip-attempts"

        with self.assertRaises(HTTPException) as raised:
            login_user(LoginRequest(name="Alice", password="correct password"), self.request(), Response())

        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(raised.exception.headers, {"Retry-After": "17"})
        self.assertEqual(self.password_hasher.verifications, [])

    def test_login_rejects_before_password_verification_when_hash_capacity_is_exhausted(self) -> None:
        semaphore = self.application.state.password_hash_semaphore
        for _ in range(self.application.state.settings.password_hash_concurrency):
            self.assertTrue(semaphore.acquire(blocking=False))
        try:
            with self.assertRaises(HTTPException) as raised:
                login_user(LoginRequest(name="Alice", password="correct password"), self.request(), Response())
        finally:
            for _ in range(self.application.state.settings.password_hash_concurrency):
                semaphore.release()

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(self.password_hasher.verifications, [])

    def test_session_validation_accepts_the_short_cookie_and_records_activity(self) -> None:
        login_response = Response(status_code=204)
        login_user(LoginRequest(name="Alice", password="correct password"), self.request(), login_response)
        token = self.cookie_value(self.cookie_headers(login_response), "moedeiro_session")

        result = validate_session(self.request({"moedeiro_session": token}))

        self.assertIsNone(result)
        with self.application.state.databases.open_registry() as unit_of_work:
            sessions = unit_of_work.auth_session_repository.list_by_user(self.user.uuid)
        self.assertIsNotNone(sessions[0].last_activity_at)

    def test_refresh_rotates_the_remember_cookie_and_issues_a_new_short_cookie(self) -> None:
        login_response = Response(status_code=204)
        login_user(LoginRequest(name="Alice", password="correct password", remember=True), self.request(), login_response)
        login_headers = self.cookie_headers(login_response)
        old_remember = self.cookie_value(login_headers, "moedeiro_remember")

        refresh_response = Response(status_code=204)
        refresh(self.request({"moedeiro_remember": old_remember}), refresh_response)

        refresh_headers = self.cookie_headers(refresh_response)
        new_remember = self.cookie_value(refresh_headers, "moedeiro_remember")
        self.assertNotEqual(new_remember, old_remember)
        self.assertTrue(any(header.startswith("moedeiro_session=") for header in refresh_headers))
        with self.assertRaises(HTTPException) as raised:
            refresh(self.request({"moedeiro_remember": old_remember}), Response())
        self.assertEqual(raised.exception.status_code, 401)

    def test_logout_revokes_both_sessions_and_clears_both_cookies(self) -> None:
        login_response = Response(status_code=204)
        login_user(LoginRequest(name="Alice", password="correct password", remember=True), self.request(), login_response)
        login_headers = self.cookie_headers(login_response)
        session_token = self.cookie_value(login_headers, "moedeiro_session")
        remember_token = self.cookie_value(login_headers, "moedeiro_remember")
        response = Response(status_code=204)

        logout_user(self.request({"moedeiro_session": session_token, "moedeiro_remember": remember_token}), response)

        headers = self.cookie_headers(response)
        self.assertEqual(sum("Max-Age=0" in header for header in headers), 2)
        with self.assertRaises(HTTPException):
            validate_session(self.request({"moedeiro_session": session_token}))
        with self.assertRaises(HTTPException):
            refresh(self.request({"moedeiro_remember": remember_token}), Response())

    def test_authentication_routes_are_exposed_without_response_bodies(self) -> None:
        paths = self.application.openapi()["paths"]

        for path, method in (
            ("/api/authentication/login", "post"),
            ("/api/authentication/session", "get"),
            ("/api/authentication/refresh", "post"),
            ("/api/authentication/logout", "post"),
        ):
            with self.subTest(path=path):
                response = paths[path][method]["responses"]["204"]
                self.assertNotIn("content", response)


if __name__ == "__main__":
    unittest.main()
