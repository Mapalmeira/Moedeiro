import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app.factory import create_app
from app.settings import Settings
from tests.fakes import FakeCredentialOperationExecutor, FakePasswordHasher, FakeRateLimiter, FakeTotpAuthenticator


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class AuthenticationHttpTest(unittest.TestCase):
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
        self.application = create_app(
            settings,
            self.password_hasher,
            FakeRateLimiter(),
            FakeTotpAuthenticator(),
            FakeCredentialOperationExecutor(),
            mount_frontend=False,
        )
        with self.application.state.databases.open_registry() as unit_of_work:
            unit_of_work.user_repository.create("Alice", self.password_hasher.hash("correct password"), 10)
            unit_of_work.commit()
        self.password_hasher.passwords.clear()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def client(self) -> TestClient:
        return TestClient(self.application, base_url="https://testserver")

    def test_password_login_sets_session_cookie_and_authenticates_protected_routes(self) -> None:
        with self.client() as client:
            login_response = client.post(
                "/api/authentication/login",
                json={"name": "Alice", "password": "correct password"},
            )

            self.assertEqual(login_response.status_code, 204)
            self.assertIsNotNone(client.cookies.get("moedeiro_session"))
            session_response = client.get("/api/authentication/session")
            ledgers_response = client.get("/api/ledgers")

        self.assertEqual(session_response.status_code, 200)
        self.assertEqual(session_response.json(), {"name": "Alice"})
        self.assertEqual(ledgers_response.status_code, 200)
        self.assertEqual(ledgers_response.json(), [])

    def test_remember_cookie_refresh_rotates_both_authentication_tokens(self) -> None:
        with self.client() as client:
            login_response = client.post(
                "/api/authentication/login",
                json={"name": "Alice", "password": "correct password", "remember": True},
            )
            self.assertEqual(login_response.status_code, 204)
            old_session = client.cookies.get("moedeiro_session")
            old_remember = client.cookies.get("moedeiro_remember")
            self.assertIsNotNone(old_session)
            self.assertIsNotNone(old_remember)

            refresh_response = client.post("/api/authentication/refresh")

            self.assertEqual(refresh_response.status_code, 204)
            self.assertNotEqual(client.cookies.get("moedeiro_session"), old_session)
            self.assertNotEqual(client.cookies.get("moedeiro_remember"), old_remember)
            self.assertEqual(client.get("/api/authentication/session").status_code, 200)

        with self.client() as stale_client:
            stale_client.cookies.set("moedeiro_remember", old_remember, path="/api/authentication")
            stale_refresh_response = stale_client.post("/api/authentication/refresh")

        self.assertEqual(stale_refresh_response.status_code, 401)
        self.assertEqual(stale_refresh_response.json(), {"detail": "Invalid session"})

    def test_logout_revokes_session_and_remember_cookie_over_http(self) -> None:
        with self.client() as client:
            login_response = client.post(
                "/api/authentication/login",
                json={"name": "Alice", "password": "correct password", "remember": True},
            )
            self.assertEqual(login_response.status_code, 204)
            old_session = client.cookies.get("moedeiro_session")
            old_remember = client.cookies.get("moedeiro_remember")
            self.assertIsNotNone(old_session)
            self.assertIsNotNone(old_remember)

            logout_response = client.post("/api/authentication/logout")

            self.assertEqual(logout_response.status_code, 204)
            self.assertIsNone(client.cookies.get("moedeiro_session"))
            self.assertIsNone(client.cookies.get("moedeiro_remember"))
            session_response = client.get("/api/authentication/session")

        self.assertEqual(session_response.status_code, 401)
        self.assertEqual(session_response.json(), {"detail": "Invalid session"})

        with self.client() as stale_client:
            stale_client.cookies.set("moedeiro_session", old_session, path="/api")
            stale_client.cookies.set("moedeiro_remember", old_remember, path="/api/authentication")
            stale_session_response = stale_client.get("/api/authentication/session")
            stale_refresh_response = stale_client.post("/api/authentication/refresh")

        self.assertEqual(stale_session_response.status_code, 401)
        self.assertEqual(stale_refresh_response.status_code, 401)
