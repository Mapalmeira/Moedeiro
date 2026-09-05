from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest

from fastapi import HTTPException, Request

from app.api.dependencies.authentication import require_authenticated_user
from app.application.registry.use_cases.authentication import login
from app.factory import create_app
from app.infrastructure.security.rate_limiter import RateLimiter
from app.settings import Settings
from tests.fakes import FakeCredentialOperationExecutor, FakePasswordHasher, FakeTotpAuthenticator


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class AuthenticatedUserRateLimitTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        directory = Path(self.temporary_directory.name)
        self.password_hasher = FakePasswordHasher()
        self.application = create_app(
            Settings(
                registry_schema_path=REGISTRY_SCHEMA_PATH,
                ledger_schema_path=LEDGER_SCHEMA_PATH,
                registry_db_path=directory / "registry/registry.sqlite",
                ledger_dbs_dir=directory / "ledgers",
                authenticated_user_operations_rate_limit="2/minute",
            ),
            self.password_hasher,
            RateLimiter(),
            FakeTotpAuthenticator(),
            FakeCredentialOperationExecutor(),
            mount_frontend=False,
        )
        with self.application.state.databases.open_registry() as unit_of_work:
            self.alice = unit_of_work.user_repository.create("Alice", self.password_hasher.hash("alice password"), 10)
            self.bob = unit_of_work.user_repository.create("Bob", self.password_hasher.hash("bob password"), 10)
            unit_of_work.commit()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def request_for(self, name: str, password: str) -> Request:
        token, _ = login(self.application.state.databases.open_registry, self.password_hasher, name, password, False, int(time.time()))
        return Request({"type": "http", "app": self.application, "client": ("192.0.2.1", 50000), "headers": [(b"cookie", f"moedeiro_session={token}".encode("ascii"))]})

    def test_limit_is_shared_by_a_user_without_affecting_another_user(self) -> None:
        first_alice_session = self.request_for("Alice", "alice password")
        second_alice_session = self.request_for("Alice", "alice password")
        bob_session = self.request_for("Bob", "bob password")

        self.assertEqual(require_authenticated_user(first_alice_session), self.alice)
        self.assertEqual(require_authenticated_user(second_alice_session), self.alice)
        with self.assertRaises(HTTPException) as raised:
            require_authenticated_user(first_alice_session)
        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(require_authenticated_user(bob_session), self.bob)


if __name__ == "__main__":
    unittest.main()
