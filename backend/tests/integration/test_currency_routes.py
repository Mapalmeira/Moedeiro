from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from fastapi import HTTPException, Request
from pydantic import ValidationError

from app.api.currency import create_ledger_currency, delete_ledger_currency, get_ledger_currency, list_ledger_currencies, update_ledger_currency
from app.api.ledger import create_owned_ledger
from app.api.schema.currency import CreateCurrencyRequest, UpdateCurrencyRequest
from app.api.schema.ledger import CreateLedgerRequest
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
        )
        with self.application.state.databases.open_registry() as unit_of_work:
            self.user = unit_of_work.user_repository.create("Alice", "$argon2id$test", 10)
            self.other_user = unit_of_work.user_repository.create("Bob", "$argon2id$test", 10)
            unit_of_work.commit()
        self.request = Request({"type": "http", "app": self.application, "client": ("192.0.2.1", 50000), "headers": []})
        self.ledger = create_owned_ledger(
            CreateLedgerRequest(name="Household", icon="WalletCards", color_code="#102030"),
            self.request,
            self.user,
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def create_currency(self, name: str = "Real", decimal_places: int = 2):
        return create_ledger_currency(
            self.ledger.uuid,
            CreateCurrencyRequest(
                name=name,
                prefix="R$",
                suffix=None,
                decimal_places=decimal_places,
                icon="CircleDollarSign",
                color_code="#AABBCC",
            ),
            self.request,
            self.user,
        )

    def test_create_and_get_return_the_persisted_currency(self) -> None:
        created = self.create_currency()

        response = get_ledger_currency(self.ledger.uuid, created.uuid, self.request, self.user)

        self.assertEqual(response, created)
        self.assertEqual(response.color_code, "#AABBCC")

    def test_list_all_and_page_apply_the_requested_order(self) -> None:
        charlie = self.create_currency("Charlie")
        alpha = self.create_currency("Alpha")
        bravo = self.create_currency("Bravo")

        all_currencies = list_ledger_currencies(self.ledger.uuid, self.request, self.user, 1, 3, "name", False)
        page = list_ledger_currencies(self.ledger.uuid, self.request, self.user, 2, 1, "name", True)

        self.assertEqual(all_currencies, [charlie, bravo, alpha])
        self.assertEqual(page, [bravo])

    def test_list_rejects_a_page_larger_than_the_configured_limit(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            list_ledger_currencies(self.ledger.uuid, self.request, self.user, 1, 4, "name", True)

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(raised.exception.detail, "page_size must be less than or equal to 3")

    def test_update_preserves_decimal_places(self) -> None:
        created = self.create_currency(decimal_places=3)

        updated = update_ledger_currency(
            self.ledger.uuid,
            created.uuid,
            UpdateCurrencyRequest(name="Brazilian Real", prefix=None, suffix=" BRL", icon="Banknote", color_code="#010203"),
            self.request,
            self.user,
        )

        self.assertEqual(updated.name, "Brazilian Real")
        self.assertEqual(updated.decimal_places, 3)
        self.assertEqual(updated.color_code, "#010203")

    def test_delete_returns_not_found_after_removing_an_unused_currency(self) -> None:
        created = self.create_currency()

        self.assertIsNone(delete_ledger_currency(self.ledger.uuid, created.uuid, self.request, self.user))

        with self.assertRaises(HTTPException) as raised:
            get_ledger_currency(self.ledger.uuid, created.uuid, self.request, self.user)
        self.assertEqual(raised.exception.status_code, 404)

    def test_delete_returns_conflict_when_an_account_uses_the_currency(self) -> None:
        currency = self.create_currency()
        with self.application.state.databases.open_ledger(f"{self.ledger.uuid}.sqlite") as unit_of_work:
            unit_of_work.account_repository.create("Checking", None, currency.uuid, "WalletCards", b"\x80\x80\x80")
            unit_of_work.commit()

        with self.assertRaises(HTTPException) as raised:
            delete_ledger_currency(self.ledger.uuid, currency.uuid, self.request, self.user)

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, "Currency is in use")

    def test_another_user_cannot_discover_or_change_ledger_currencies(self) -> None:
        currency = self.create_currency()

        operations = (
            lambda: list_ledger_currencies(self.ledger.uuid, self.request, self.other_user, 1, 3, "name", True),
            lambda: get_ledger_currency(self.ledger.uuid, currency.uuid, self.request, self.other_user),
            lambda: update_ledger_currency(
                self.ledger.uuid,
                currency.uuid,
                UpdateCurrencyRequest(name="Stolen", prefix=None, suffix=None, icon="Banknote", color_code="#000000"),
                self.request,
                self.other_user,
            ),
            lambda: delete_ledger_currency(self.ledger.uuid, currency.uuid, self.request, self.other_user),
        )

        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaises(HTTPException) as raised:
                    operation()
                self.assertEqual(raised.exception.status_code, 404)
                self.assertEqual(raised.exception.detail, "Ledger not found")

    def test_missing_currency_and_ledger_return_not_found(self) -> None:
        for ledger_uuid, currency_uuid, detail in (
            (self.ledger.uuid, uuid4(), "Currency not found"),
            (uuid4(), uuid4(), "Ledger not found"),
        ):
            with self.subTest(detail=detail):
                with self.assertRaises(HTTPException) as raised:
                    get_ledger_currency(ledger_uuid, currency_uuid, self.request, self.user)
                self.assertEqual(raised.exception.status_code, 404)
                self.assertEqual(raised.exception.detail, detail)

    def test_request_schemas_reject_invalid_currency_data(self) -> None:
        invalid_values = (
            {"name": "", "prefix": None, "suffix": None, "decimal_places": 2, "icon": "DollarSign", "color_code": "#102030"},
            {"name": "Real", "prefix": None, "suffix": None, "decimal_places": -1, "icon": "DollarSign", "color_code": "#102030"},
            {"name": "Real", "prefix": None, "suffix": None, "decimal_places": 2, "icon": "DollarSign", "color_code": "red"},
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
        page_size = next(parameter for parameter in collection["get"]["parameters"] if parameter["name"] == "page_size")
        self.assertEqual(page_size["schema"]["minimum"], 1)
        self.assertNotIn("maximum", page_size["schema"])
        self.assertIn("200", member["get"]["responses"])
        self.assertIn("200", member["put"]["responses"])
        self.assertNotIn("content", member["delete"]["responses"]["204"])


if __name__ == "__main__":
    unittest.main()
