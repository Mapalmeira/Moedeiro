import unittest
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch
from app.factory import _create_totp_authenticator, create_app
from app.application.ledger.exceptions import QueryResultOverflowError
from app.infrastructure.persistence.sqlite.databases import SqliteDatabases
from app.settings import Settings
from tests.fakes import FakeCredentialOperationExecutor, FakePasswordHasher, FakeRateLimiter, FakeTotpAuthenticator


ROOT = Path(__file__).resolve().parents[3]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class ApplicationFactoryTest(unittest.TestCase):
    def settings(self, directory: Path, **overrides) -> Settings:
        return Settings(
            registry_schema_path=REGISTRY_SCHEMA_PATH,
            ledger_schema_path=LEDGER_SCHEMA_PATH,
            registry_db_path=directory / "registry/registry.sqlite",
            ledger_dbs_dir=directory / "ledgers",
            **overrides,
        )

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
            self.assertTrue({"/api/authentication/login", "/api/authentication/logout", "/api/ledgers", "/api/ledgers/{ledger_uuid}", "/api/ledgers/{ledger_uuid}/accounts", "/api/ledgers/{ledger_uuid}/accounts/{account_uuid}", "/api/ledgers/{ledger_uuid}/balances", "/api/ledgers/{ledger_uuid}/accounts/{account_uuid}/balance", "/api/ledgers/{ledger_uuid}/accounts/{account_uuid}/balance/points", "/api/ledgers/{ledger_uuid}/budgets", "/api/ledgers/{ledger_uuid}/budgets/overview", "/api/ledgers/{ledger_uuid}/budgets/currency-overview", "/api/ledgers/{ledger_uuid}/budgets/{budget_uuid}", "/api/ledgers/{ledger_uuid}/cash-flow", "/api/ledgers/{ledger_uuid}/cash-flow/points", "/api/ledgers/{ledger_uuid}/categories", "/api/ledgers/{ledger_uuid}/categories/tree", "/api/ledgers/{ledger_uuid}/categories/{category_uuid}", "/api/ledgers/{ledger_uuid}/currencies", "/api/ledgers/{ledger_uuid}/currencies/{currency_uuid}", "/api/ledgers/{ledger_uuid}/events", "/api/ledgers/{ledger_uuid}/events/{event_uuid}", "/api/password/change", "/api/password/recovery", "/api/registration"}.issubset(application.openapi()["paths"]))
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

    def test_create_app_mounts_the_frontend_when_enabled(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            settings = self.settings(Path(temporary_directory))
            with patch("app.factory._mount_frontend") as mount_frontend:
                application = create_app(
                    settings,
                    totp_authenticator=FakeTotpAuthenticator(),
                    credential_operation_executor=FakeCredentialOperationExecutor(),
                )

            mount_frontend.assert_called_once_with(application, settings.frontend_dist_path)

    def test_numeric_error_handlers_return_safe_responses(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            application = create_app(
                self.settings(Path(temporary_directory)),
                totp_authenticator=FakeTotpAuthenticator(),
                credential_operation_executor=FakeCredentialOperationExecutor(),
                mount_frontend=False,
            )
        overflow_handler = application.exception_handlers[OverflowError]
        query_handler = application.exception_handlers[QueryResultOverflowError]

        binding = asyncio.run(overflow_handler(None, OverflowError("Python int too large to convert to SQLite INTEGER")))
        unexpected = asyncio.run(overflow_handler(None, OverflowError("unexpected")))
        query = asyncio.run(query_handler(None, QueryResultOverflowError()))

        self.assertEqual((binding.status_code, binding.body), (422, b'{"detail":"Integer must fit signed 64-bit range"}'))
        self.assertEqual((unexpected.status_code, unexpected.body), (500, b'{"detail":"Internal Server Error"}'))
        self.assertEqual((query.status_code, query.body), (422, b'{"detail":"Query result exceeds signed 64-bit range"}'))

    def test_create_app_selects_environment_settings_and_default_collaborators(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            settings = self.settings(Path(temporary_directory), totp_encryption_key="test-key")
            password_hasher = FakePasswordHasher()
            totp_authenticator = FakeTotpAuthenticator()
            executor = FakeCredentialOperationExecutor()
            rate_limiter = FakeRateLimiter()
            with (
                patch("app.factory.Settings.from_environment", return_value=settings),
                patch("app.factory._create_password_hasher", return_value=password_hasher),
                patch("app.factory._create_totp_authenticator", return_value=totp_authenticator),
                patch("app.factory.CredentialOperationExecutor", return_value=executor),
                patch("app.factory.RateLimiter", return_value=rate_limiter),
            ):
                application = create_app(mount_frontend=False)

            self.assertIs(application.state.settings, settings)
            self.assertIs(application.state.totp_authenticator, totp_authenticator)
            self.assertIs(application.state.credential_operation_executor, executor)
            self.assertIs(application.state.rate_limiter, rate_limiter)

    def test_totp_authenticator_requires_a_configured_encryption_key(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            settings = self.settings(Path(temporary_directory))
            with self.assertRaisesRegex(ValueError, "TOTP_ENCRYPTION_KEY must be defined"):
                _create_totp_authenticator(settings)

            configured = self.settings(Path(temporary_directory), totp_encryption_key="test-key")
            with patch("app.infrastructure.security.totp_authenticator.FernetTotpAuthenticator", return_value=FakeTotpAuthenticator()) as authenticator:
                result = _create_totp_authenticator(configured)

            self.assertIsInstance(result, FakeTotpAuthenticator)
            authenticator.assert_called_once_with("test-key")


    def test_frontend_mount_uses_the_configured_build_path(self) -> None:
        from app.factory import _mount_frontend

        application = MagicMock()
        frontend_directory = ROOT.parent / "frontend/dist/moedeiro/browser"
        _mount_frontend(application, frontend_directory)

        application.frontend.assert_called_once_with(
            "/",
            directory=frontend_directory,
            fallback="index.html",
        )
