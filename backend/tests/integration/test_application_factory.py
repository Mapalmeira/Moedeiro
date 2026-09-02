from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.factory import create_app
from app.infrastructure.persistence.sqlite.databases import SqliteDatabases
from app.settings import Settings
from tests.fakes import FakePasswordHasher, FakeRateLimiter, FakeTotpAuthenticator


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
            application = create_app(settings, password_hasher, rate_limiter, totp_authenticator)

            self.assertIs(application.state.settings, settings)
            self.assertIsInstance(application.state.databases, SqliteDatabases)
            self.assertIs(application.state.password_hasher, password_hasher)
            self.assertIs(application.state.rate_limiter, rate_limiter)
            self.assertIs(application.state.totp_authenticator, totp_authenticator)
            for _ in range(settings.password_hash_concurrency):
                self.assertTrue(application.state.password_hash_semaphore.acquire(blocking=False))
            self.assertFalse(application.state.password_hash_semaphore.acquire(blocking=False))
            for _ in range(settings.password_hash_concurrency):
                application.state.password_hash_semaphore.release()
            self.assertTrue({"/api/authentication/login", "/api/authentication/logout", "/api/password/change", "/api/password/recovery", "/api/registration"}.issubset(application.openapi()["paths"]))
            self.assertTrue(settings.registry_db_path.is_file())
            self.assertTrue(settings.ledger_dbs_dir.is_dir())


if __name__ == "__main__":
    unittest.main()
