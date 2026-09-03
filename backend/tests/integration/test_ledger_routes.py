from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from fastapi import HTTPException, Request
from pydantic import ValidationError

from app.api.ledger import create_owned_ledger, delete_user_ledger, get_user_ledger, list_user_ledgers, update_user_ledger
from app.api.schema.ledger import CreateLedgerRequest, UpdateLedgerRequest
from app.factory import create_app
from app.settings import Settings
from tests.fakes import FakeCredentialOperationExecutor, FakePasswordHasher, FakeRateLimiter, FakeTotpAuthenticator


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class LedgerRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        directory = Path(self.temporary_directory.name)
        settings = Settings(
            registry_schema_path=REGISTRY_SCHEMA_PATH,
            ledger_schema_path=LEDGER_SCHEMA_PATH,
            registry_db_path=directory / "registry/registry.sqlite",
            ledger_dbs_dir=directory / "ledgers",
        )
        self.application = create_app(
            settings,
            FakePasswordHasher(),
            FakeRateLimiter(),
            FakeTotpAuthenticator(),
            FakeCredentialOperationExecutor(),
        )
        with self.application.state.databases.open_registry() as unit_of_work:
            self.alice = unit_of_work.user_repository.create("Alice", "$argon2id$test", 10)
            self.bob = unit_of_work.user_repository.create("Bob", "$argon2id$test", 10)
            unit_of_work.commit()
        self.request = Request({"type": "http", "app": self.application, "client": ("192.0.2.1", 50000), "headers": []})

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def create_ledger(self, name="Household"):
        return create_owned_ledger(
            CreateLedgerRequest(name=name, icon="WalletCards", color_code="#102030"),
            self.request,
            self.alice,
        )

    def test_create_and_list_return_only_public_ledger_data(self) -> None:
        created = self.create_ledger()

        listed = list_user_ledgers(self.request, self.alice)

        self.assertEqual(listed, [created])
        self.assertEqual(created.color_code, "#102030")
        self.assertTrue(self.application.state.databases.get_ledger_path(created.uuid).is_file())
        self.assertNotIn("path", created.model_dump())

    def test_list_applies_the_requested_name_order(self) -> None:
        bravo = self.create_ledger("Bravo")
        alpha = self.create_ledger("Alpha")

        listed = list_user_ledgers(self.request, self.alice, "name", False)

        self.assertEqual(listed, [bravo, alpha])

    def test_access_resolves_only_the_owner_ledger(self) -> None:
        created = self.create_ledger()

        response = get_user_ledger(created.uuid, self.request, self.alice)

        self.assertEqual(response, created)
        with self.application.state.databases.open_ledger(f"{created.uuid}.sqlite") as unit_of_work:
            metadata = unit_of_work.ledger_metadata_repository.get()
        assert metadata is not None
        self.assertEqual(metadata.ledger_uuid, created.uuid)

    def test_get_update_and_delete_follow_the_owner_grant(self) -> None:
        created = self.create_ledger()
        ledger_path = self.application.state.databases.get_ledger_path(created.uuid)

        updated = update_user_ledger(
            created.uuid,
            UpdateLedgerRequest(name="Personal", icon="PiggyBank", color_code="#AABBCC"),
            self.request,
            self.alice,
        )
        result = delete_user_ledger(created.uuid, self.request, self.alice)

        self.assertEqual(updated.name, "Personal")
        self.assertEqual(updated.color_code, "#AABBCC")
        self.assertIsNone(result)
        self.assertFalse(ledger_path.exists())
        with self.assertRaises(HTTPException) as raised:
            get_user_ledger(created.uuid, self.request, self.alice)
        self.assertEqual(raised.exception.status_code, 404)

    def test_another_user_receives_the_same_not_found_response_for_every_ledger_uuid(self) -> None:
        created = self.create_ledger()

        for ledger_uuid in (created.uuid, uuid4()):
            with self.subTest(ledger_uuid=ledger_uuid):
                with self.assertRaises(HTTPException) as raised:
                    get_user_ledger(ledger_uuid, self.request, self.bob)
                self.assertEqual(raised.exception.status_code, 404)
                self.assertEqual(raised.exception.detail, "Ledger not found")

        with self.assertRaises(HTTPException) as raised:
            update_user_ledger(
                created.uuid,
                UpdateLedgerRequest(name="Stolen", icon="Wallet", color_code="#000000"),
                self.request,
                self.bob,
            )
        self.assertEqual(raised.exception.status_code, 404)
        with self.assertRaises(HTTPException) as raised:
            delete_user_ledger(created.uuid, self.request, self.bob)
        self.assertEqual(raised.exception.status_code, 404)

    def test_request_schemas_reject_invalid_names_icons_and_colors(self) -> None:
        invalid_values = (
            {"name": "", "icon": "Wallet", "color_code": "#102030"},
            {"name": "Ledger", "icon": "", "color_code": "#102030"},
            {"name": "Ledger", "icon": "Wallet", "color_code": "red"},
        )

        for values in invalid_values:
            with self.subTest(values=values):
                with self.assertRaises(ValidationError):
                    CreateLedgerRequest(**values)

    def test_routes_expose_expected_status_codes_and_response_schemas(self) -> None:
        paths = self.application.openapi()["paths"]

        self.assertIn("201", paths["/api/ledgers"]["post"]["responses"])
        self.assertIn("200", paths["/api/ledgers"]["get"]["responses"])
        self.assertIn("200", paths["/api/ledgers/{ledger_uuid}"]["get"]["responses"])
        self.assertIn("200", paths["/api/ledgers/{ledger_uuid}"]["put"]["responses"])
        delete_response = paths["/api/ledgers/{ledger_uuid}"]["delete"]["responses"]["204"]
        self.assertNotIn("content", delete_response)


if __name__ == "__main__":
    unittest.main()
