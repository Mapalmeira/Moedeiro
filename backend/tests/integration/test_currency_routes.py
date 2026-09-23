import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi import HTTPException, Request
from pydantic import ValidationError

from app.api.dependencies.ledger import require_granted_ledger
from app.api.ledger.routes.currency import create_ledger_currency, delete_ledger_currency, get_ledger_currency, list_ledger_currencies, update_ledger_currency
from app.api.registry.routes.ledger import create_owned_ledger
from app.api.ledger.schema.currency import CreateCurrencyRequest, UpdateCurrencyRequest
from app.api.registry.schema.ledger import CreateLedgerRequest
from app.factory import create_app
from app.settings import Settings
from tests.fakes import FakeCredentialOperationExecutor, FakePasswordHasher, FakeRateLimiter, FakeTotpAuthenticator


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class CurrencyRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        directory = Path(self.temporary_directory.name)
        self.application = create_app(
            Settings(
                registry_schema_path=REGISTRY_SCHEMA_PATH,
                ledger_schema_path=LEDGER_SCHEMA_PATH,
                registry_db_path=directory / "registry/registry.sqlite",
                ledger_dbs_dir=directory / "ledgers",
                max_page_size=3,
            ),
            FakePasswordHasher(),
            FakeRateLimiter(),
            FakeTotpAuthenticator(),
            FakeCredentialOperationExecutor(),
            mount_frontend=False,
        )
        with self.application.state.databases.open_registry() as unit_of_work:
            self.user = unit_of_work.user_repository.create("Alice", "$argon2id$test", 10)
            unit_of_work.commit()
        self.request = Request({"type": "http", "app": self.application, "client": ("192.0.2.1", 50000), "headers": []})
        self.ledger = create_owned_ledger(
            CreateLedgerRequest(name="Household", icon="lucide:WalletCards", color_code="#102030"),
            self.request,
            self.user,
        )
        self.ledger = require_granted_ledger(self.request, self.user, self.ledger.uuid)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def create_currency(self, name: str = "Test currency", decimal_places: int = 2):
        return create_ledger_currency(
            self.ledger.uuid,
            CreateCurrencyRequest(
                name=name,
                prefix="R$",
                suffix=None,
                decimal_places=decimal_places,
                icon="lucide:CircleDollarSign",
                color_code="#AABBCC",
            ),
            self.request,
            self.ledger,
        )

    def test_create_and_get_return_the_persisted_currency(self) -> None:
        created = self.create_currency()

        response = get_ledger_currency(self.ledger.uuid, created.uuid, self.request, self.ledger)

        self.assertEqual(response, created)
        self.assertEqual(response.color_code, "#AABBCC")

    def test_create_returns_conflict_for_an_unavailable_name(self) -> None:
        self.create_currency("Unique test currency")

        with self.assertRaises(HTTPException) as raised:
            self.create_currency("Unique test currency")

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, "Currency name unavailable")

    def test_list_returns_the_entire_collection_without_page_limits(self) -> None:
        initial = list_ledger_currencies(self.ledger.uuid, self.request, self.ledger)
        created = [self.create_currency(name) for name in ("Charlie", "Alpha", "Bravo", "Delta")]
        self.assertEqual(list_ledger_currencies(self.ledger.uuid, self.request, self.ledger), initial + created)

    def test_creation_limit_can_be_reused_after_deletion(self) -> None:
        initial = list_ledger_currencies(self.ledger.uuid, self.request, self.ledger)
        created = [self.create_currency(f"Item {index}") for index in range(300 - len(initial))]
        with self.assertRaises(HTTPException) as raised:
            self.create_currency("Overflow")
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, "Currency limit reached")
        delete_ledger_currency(self.ledger.uuid, created[-1].uuid, self.request, self.ledger)
        self.create_currency("Replacement")
        self.assertEqual(len(list_ledger_currencies(self.ledger.uuid, self.request, self.ledger)), 300)

    def test_update_preserves_decimal_places(self) -> None:
        created = self.create_currency(decimal_places=3)

        updated = update_ledger_currency(
            self.ledger.uuid,
            created.uuid,
            UpdateCurrencyRequest(name="Brazilian Real", prefix=None, suffix=" BRL", icon="lucide:Banknote", color_code="#010203"),
            self.request,
            self.ledger,
        )

        self.assertEqual(updated.name, "Brazilian Real")
        self.assertEqual(updated.decimal_places, 3)
        self.assertEqual(updated.color_code, "#010203")

    def test_update_returns_conflict_for_an_unavailable_name(self) -> None:
        first = self.create_currency("First test currency")
        second = self.create_currency("Second test currency")

        with self.assertRaises(HTTPException) as raised:
            update_ledger_currency(
                self.ledger.uuid,
                second.uuid,
                UpdateCurrencyRequest(name=first.name, prefix=None, suffix=None, icon="lucide:Banknote", color_code="#010203"),
                self.request,
                self.ledger,
            )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, "Currency name unavailable")

    def test_delete_returns_not_found_after_removing_an_unused_currency(self) -> None:
        created = self.create_currency()

        self.assertIsNone(delete_ledger_currency(self.ledger.uuid, created.uuid, self.request, self.ledger))

        with self.assertRaises(HTTPException) as raised:
            get_ledger_currency(self.ledger.uuid, created.uuid, self.request, self.ledger)
        self.assertEqual(raised.exception.status_code, 404)

    def test_delete_returns_conflict_when_an_account_uses_the_currency(self) -> None:
        currency = self.create_currency()
        with self.application.state.databases.open_ledger(f"{self.ledger.uuid}.sqlite") as unit_of_work:
            unit_of_work.account_repository.create("Checking", None, currency.uuid, "lucide:WalletCards", b"\x80\x80\x80")
            unit_of_work.commit()

        with self.assertRaises(HTTPException) as raised:
            delete_ledger_currency(self.ledger.uuid, currency.uuid, self.request, self.ledger)

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, "Currency is in use")

    def test_missing_currency_returns_not_found(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            get_ledger_currency(self.ledger.uuid, uuid4(), self.request, self.ledger)

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(raised.exception.detail, "Currency not found")

    def test_request_schemas_reject_invalid_currency_data(self) -> None:
        invalid_values = (
            {"name": "", "prefix": None, "suffix": None, "decimal_places": 2, "icon": "lucide:DollarSign", "color_code": "#102030"},
            {"name": "Real", "prefix": None, "suffix": None, "decimal_places": -1, "icon": "lucide:DollarSign", "color_code": "#102030"},
            {"name": "Real", "prefix": None, "suffix": None, "decimal_places": 2, "icon": "DollarSign", "color_code": "#102030"},
            {"name": "Real", "prefix": None, "suffix": None, "decimal_places": 2, "icon": "lucide:DollarSign", "color_code": "red"},
        )

        for values in invalid_values:
            with self.subTest(values=values):
                with self.assertRaises(ValidationError):
                    CreateCurrencyRequest(**values)

    def test_routes_expose_the_complete_currency_lifecycle(self) -> None:
        paths = self.application.openapi()["paths"]
        collection = paths["/api/ledgers/{ledger_uuid}/currencies"]
        member = paths["/api/ledgers/{ledger_uuid}/currencies/{currency_uuid}"]

        self.assertIn("201", collection["post"]["responses"])
        self.assertIn("200", collection["get"]["responses"])
        self.assertNotIn("/api/ledgers/{ledger_uuid}/currencies/page", paths)
        query_parameters = [p for p in collection["get"]["parameters"] if p["in"] == "query"]
        self.assertEqual(query_parameters, [])
        self.assertIn("200", member["get"]["responses"])
        self.assertIn("200", member["put"]["responses"])
        self.assertNotIn("content", member["delete"]["responses"]["204"])
