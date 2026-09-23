import unittest
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies.authentication import require_ledger_grantee
from app.factory import create_app
from app.infrastructure.security.rate_limiter import RateLimiter
from app.settings import Settings
from tests.fakes import FakeCredentialOperationExecutor, FakePasswordHasher, FakeTotpAuthenticator


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class ExternalAccessRateLimitTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        directory = Path(self.temporary_directory.name)
        self.application = create_app(
            Settings(
                registry_schema_path=REGISTRY_SCHEMA_PATH,
                ledger_schema_path=LEDGER_SCHEMA_PATH,
                registry_db_path=directory / "registry/registry.sqlite",
                ledger_dbs_dir=directory / "ledgers",
                external_access_operations_rate_limit="2/minute",
            ),
            FakePasswordHasher(),
            RateLimiter(),
            FakeTotpAuthenticator(),
            FakeCredentialOperationExecutor(),
            mount_frontend=False,
        )
        with self.application.state.databases.open_registry() as unit_of_work:
            self.first = unit_of_work.external_access_repository.create("First", hashlib.sha256(b"first-token").digest())
            self.second = unit_of_work.external_access_repository.create("Second", hashlib.sha256(b"second-token").digest())
            unit_of_work.commit()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def request(self, token: str) -> Request:
        return Request(
            {
                "type": "http",
                "app": self.application,
                "client": ("192.0.2.1", 50000),
                "headers": [(b"authorization", f"Bearer {token}".encode("ascii"))],
            }
        )

    def credentials(self, token: str) -> HTTPAuthorizationCredentials:
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    def test_limit_is_shared_across_external_accesses(self) -> None:
        first_request = self.request("first-token")
        first_credentials = self.credentials("first-token")
        second_request = self.request("second-token")
        second_credentials = self.credentials("second-token")

        self.assertEqual(require_ledger_grantee(first_request, first_credentials), self.first)
        self.assertEqual(require_ledger_grantee(second_request, second_credentials), self.second)
        with self.assertRaises(HTTPException) as raised:
            require_ledger_grantee(first_request, first_credentials)
        self.assertEqual(raised.exception.status_code, 429)
        with self.assertRaises(HTTPException) as raised:
            require_ledger_grantee(second_request, second_credentials)
        self.assertEqual(raised.exception.status_code, 429)
