import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.api.routes.health import health_check
from app.factory import create_app
from app.settings import Settings
from tests.fakes import FakeCredentialOperationExecutor, FakePasswordHasher, FakeRateLimiter, FakeTotpAuthenticator


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class HealthRouteTest(unittest.TestCase):
    def test_health_check_has_no_dependencies_or_response_body(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            application = create_app(
                Settings(
                    registry_schema_path=REGISTRY_SCHEMA_PATH,
                    ledger_schema_path=LEDGER_SCHEMA_PATH,
                    registry_db_path=directory / "registry/registry.sqlite",
                    ledger_dbs_dir=directory / "ledgers",
                ),
                FakePasswordHasher(),
                FakeRateLimiter(),
                FakeTotpAuthenticator(),
                FakeCredentialOperationExecutor(),
                mount_frontend=False,
            )

            self.assertIsNone(health_check())
            operation = application.openapi()["paths"]["/health"]["get"]
            self.assertNotIn("content", operation["responses"]["204"])


if __name__ == "__main__":
    unittest.main()
