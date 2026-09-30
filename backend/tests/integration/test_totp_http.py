import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app.factory import create_app
from app.settings import Settings
from tests.fakes import FakeCredentialOperationExecutor, FakePasswordHasher, FakeRateLimiter, FakeTotpAuthenticator


ROOT = Path(__file__).resolve().parents[2]


class TotpHttpTest(unittest.TestCase):
    def test_get_status_route_is_exposed_and_requires_authentication(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            application = create_app(
                Settings(
                    registry_schema_path=ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql",
                    ledger_schema_path=ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql",
                    registry_db_path=directory / "registry/registry.sqlite",
                    ledger_dbs_dir=directory / "ledgers",
                ),
                FakePasswordHasher(),
                FakeRateLimiter(),
                FakeTotpAuthenticator(),
                FakeCredentialOperationExecutor(),
                mount_frontend=False,
            )
            self.assertIn("200", application.openapi()["paths"]["/api/totp"]["get"]["responses"])

            with TestClient(application) as client:
                response = client.get("/api/totp")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Invalid session"})
