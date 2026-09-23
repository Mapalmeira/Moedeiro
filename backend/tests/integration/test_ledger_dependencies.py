import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import HTTPException, Request

from app.api.dependencies.ledger import ledger_unit_of_work_factory, require_granted_ledger
from app.api.registry.routes.ledger import create_owned_ledger
from app.api.registry.schema.ledger import CreateLedgerRequest
from app.factory import create_app
from app.settings import Settings
from tests.fakes import FakeCredentialOperationExecutor, FakePasswordHasher, FakeRateLimiter, FakeTotpAuthenticator


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class LedgerDependenciesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        directory = Path(self.temporary_directory.name)
        self.application = create_app(
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
        with self.application.state.databases.open_registry() as unit_of_work:
            self.owner = unit_of_work.user_repository.create("Alice", "$argon2id$test", 10)
            self.other_user = unit_of_work.user_repository.create("Bob", "$argon2id$test", 10)
            unit_of_work.commit()
        self.request = Request({"type": "http", "app": self.application, "client": ("192.0.2.1", 50000), "headers": []})
        self.ledger = create_owned_ledger(
            CreateLedgerRequest(name="Household", icon="lucide:WalletCards", color_code="#102030"),
            self.request,
            self.owner,
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_granted_ledger_authorizes_the_grantee_before_opening_the_ledger_database(self) -> None:
        granted = require_granted_ledger(self.request, self.owner, self.ledger.uuid)

        with ledger_unit_of_work_factory(self.request, granted)() as unit_of_work:
            currencies = unit_of_work.currency_repository.list_all()

        self.assertEqual(granted.uuid, self.ledger.uuid)
        self.assertGreater(len(currencies), 0)

    def test_granted_ledger_rejects_a_user_without_a_grant(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            require_granted_ledger(self.request, self.other_user, self.ledger.uuid)

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(raised.exception.detail, "Ledger not found")

    def test_granted_ledger_accepts_an_external_access_guest_only_for_its_ledger(self) -> None:
        with self.application.state.databases.open_registry() as unit_of_work:
            access = unit_of_work.external_access_repository.create("Plugin", b"t" * 32)
            unit_of_work.ledger_grant_repository.create(access.uuid, self.ledger.uuid, "GUEST", 20)
            unit_of_work.commit()

        granted = require_granted_ledger(self.request, access, self.ledger.uuid)

        self.assertEqual(granted.uuid, self.ledger.uuid)
