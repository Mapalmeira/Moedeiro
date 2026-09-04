import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

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
            application = create_app(settings, password_hasher, rate_limiter, totp_authenticator, credential_operation_executor)

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
            application = create_app(settings, totp_authenticator=FakeTotpAuthenticator(), credential_operation_executor=FakeCredentialOperationExecutor())

            async def assert_limit() -> None:
                from anyio.to_thread import current_default_thread_limiter

                async with application.router.lifespan_context(application):
                    self.assertEqual(current_default_thread_limiter().total_tokens, 12)

            asyncio.run(assert_limit())


if __name__ == "__main__":
    unittest.main()
