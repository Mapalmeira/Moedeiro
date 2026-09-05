import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.factory import create_app
from app.infrastructure.persistence.sqlite.databases import SqliteDatabases
from app.settings import Settings
from tests.fakes import FakeCredentialOperationExecutor, FakePasswordHasher, FakeRateLimiter, FakeTotpAuthenticator


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class ApplicationFactoryTest(unittest.TestCase):
    def test_create_app_initializes_and_exposes_its_configuration_and_databases(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            settings = Settings(
                registry_schema_path=REGISTRY_SCHEMA_PATH,
                ledger_schema_path=LEDGER_SCHEMA_PATH,
                registry_db_path=directory / "registry/registry.sqlite",
                ledger_dbs_dir=directory / "ledgers",
            )

            password_hasher = FakePasswordHasher()
            rate_limiter = FakeRateLimiter()
            totp_authenticator = FakeTotpAuthenticator()
            credential_operation_executor = FakeCredentialOperationExecutor()
            application = create_app(settings, password_hasher, rate_limiter, totp_authenticator, credential_operation_executor, mount_frontend=False)

            self.assertIs(application.state.settings, settings)
            self.assertIsInstance(application.state.databases, SqliteDatabases)
            self.assertTrue(application.state.password_hasher.verify("$argon2id$test$password", "password"))
            self.assertIs(application.state.rate_limiter, rate_limiter)
            self.assertIs(application.state.totp_authenticator, totp_authenticator)
            self.assertIs(application.state.credential_operation_executor, credential_operation_executor)
            for _ in range(settings.password_hash_concurrency):
                self.assertTrue(application.state.password_hash_semaphore.acquire(blocking=False))
            self.assertFalse(application.state.password_hash_semaphore.acquire(blocking=False))
            for _ in range(settings.password_hash_concurrency):
                application.state.password_hash_semaphore.release()
            self.assertTrue({"/api/authentication/login", "/api/authentication/logout", "/api/ledgers", "/api/ledgers/{ledger_uuid}", "/api/ledgers/{ledger_uuid}/accounts", "/api/ledgers/{ledger_uuid}/accounts/{account_uuid}", "/api/ledgers/{ledger_uuid}/accounts/{account_uuid}/balance", "/api/ledgers/{ledger_uuid}/accounts/{account_uuid}/balance/points", "/api/ledgers/{ledger_uuid}/budgets", "/api/ledgers/{ledger_uuid}/budgets/statuses", "/api/ledgers/{ledger_uuid}/budgets/{budget_uuid}", "/api/ledgers/{ledger_uuid}/budgets/{budget_uuid}/status", "/api/ledgers/{ledger_uuid}/cash-flow", "/api/ledgers/{ledger_uuid}/cash-flow/points", "/api/ledgers/{ledger_uuid}/categories", "/api/ledgers/{ledger_uuid}/categories/tree", "/api/ledgers/{ledger_uuid}/categories/{category_uuid}", "/api/ledgers/{ledger_uuid}/currencies", "/api/ledgers/{ledger_uuid}/currencies/{currency_uuid}", "/api/ledgers/{ledger_uuid}/events", "/api/ledgers/{ledger_uuid}/events/{event_uuid}", "/api/password/change", "/api/password/recovery", "/api/registration"}.issubset(application.openapi()["paths"]))
            self.assertTrue(settings.registry_db_path.is_file())
            self.assertTrue(settings.ledger_dbs_dir.is_dir())

    def test_lifespan_configures_the_shared_synchronous_route_limit(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            settings = Settings(
                registry_schema_path=REGISTRY_SCHEMA_PATH,
                ledger_schema_path=LEDGER_SCHEMA_PATH,
                registry_db_path=directory / "registry/registry.sqlite",
                ledger_dbs_dir=directory / "ledgers",
                sync_route_concurrency=12,
            )
            application = create_app(settings, totp_authenticator=FakeTotpAuthenticator(), credential_operation_executor=FakeCredentialOperationExecutor(), mount_frontend=False)

            async def assert_limit() -> None:
                from anyio.to_thread import current_default_thread_limiter

                async with application.router.lifespan_context(application):
                    self.assertEqual(current_default_thread_limiter().total_tokens, 12)

            asyncio.run(assert_limit())

    def test_create_app_can_skip_frontend_mounting(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            settings = Settings(
                registry_schema_path=REGISTRY_SCHEMA_PATH,
                ledger_schema_path=LEDGER_SCHEMA_PATH,
                registry_db_path=directory / "registry/registry.sqlite",
                ledger_dbs_dir=directory / "ledgers",
            )

            with patch("app.factory._mount_frontend") as mount_frontend:
                create_app(
                    settings,
                    totp_authenticator=FakeTotpAuthenticator(),
                    credential_operation_executor=FakeCredentialOperationExecutor(),
                    mount_frontend=False,
                )

            mount_frontend.assert_not_called()


    def test_frontend_mount_uses_the_native_build_path_by_default(self) -> None:
        from app.factory import _mount_frontend

        application = MagicMock()
        with patch.dict("os.environ", {}, clear=True):
            _mount_frontend(application)

        application.frontend.assert_called_once_with(
            "/",
            directory=Path("frontend/dist/moedeiro/browser"),
            fallback="index.html",
        )

    def test_serves_the_frontend_and_falls_back_to_its_index_for_client_routes(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            frontend_directory = directory / "frontend"
            frontend_directory.mkdir()

            (frontend_directory / "index.html").write_text("<html>Moedeiro</html>")
            (frontend_directory / "main.js").write_text("console.log('moedeiro')")

            settings = Settings(
                registry_schema_path=REGISTRY_SCHEMA_PATH,
                ledger_schema_path=LEDGER_SCHEMA_PATH,
                registry_db_path=directory / "registry/registry.sqlite",
                ledger_dbs_dir=directory / "ledgers",
            )

            with patch.dict(
                "os.environ",
                {"FRONTEND_DIST_PATH": str(frontend_directory)},
            ):
                application = create_app(
                    settings,
                    totp_authenticator=FakeTotpAuthenticator(),
                    credential_operation_executor=FakeCredentialOperationExecutor(),
                    mount_frontend=True,
                )

            with TestClient(application) as client:
                index_response = client.get("/")
                javascript_response = client.get("/main.js")
                client_route_response = client.get(
                    "/home",
                    headers={"Accept": "text/html"},
                )

            self.assertEqual(index_response.status_code, 200)
            self.assertEqual(index_response.text, "<html>Moedeiro</html>")

            self.assertEqual(javascript_response.status_code, 200)
            self.assertEqual(javascript_response.text, "console.log('moedeiro')")

            self.assertEqual(client_route_response.status_code, 200)
            self.assertEqual(client_route_response.text, "<html>Moedeiro</html>")

if __name__ == "__main__":
    unittest.main()
