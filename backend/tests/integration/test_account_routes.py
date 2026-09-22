import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi import HTTPException, Request
from pydantic import ValidationError

from app.api.ledger.routes.account import create_ledger_account, delete_ledger_account, get_ledger_account, list_ledger_accounts, update_ledger_account
from app.api.ledger.routes.currency import create_ledger_currency
from app.api.registry.routes.ledger import create_owned_ledger
from app.api.ledger.schema.account import CreateAccountRequest, UpdateAccountRequest
from app.api.ledger.schema.currency import CreateCurrencyRequest
from app.api.registry.schema.ledger import CreateLedgerRequest
from app.factory import create_app
from app.settings import Settings
from tests.fakes import FakeCredentialOperationExecutor, FakePasswordHasher, FakeRateLimiter, FakeTotpAuthenticator


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class AccountRoutesTest(unittest.TestCase):
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
            self.other_user = unit_of_work.user_repository.create("Bob", "$argon2id$test", 10)
            unit_of_work.commit()
        self.request = Request({"type": "http", "app": self.application, "client": ("192.0.2.1", 50000), "headers": []})
        self.ledger = create_owned_ledger(CreateLedgerRequest(name="Household", icon="lucide:WalletCards", color_code="#102030"), self.request, self.user)
        self.currency = create_ledger_currency(
            self.ledger.uuid,
            CreateCurrencyRequest(name="Route Real", prefix="R$", suffix=None, decimal_places=2, icon="lucide:CircleDollarSign", color_code="#AABBCC"),
            self.request,
            self.user,
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def create_account(self, name: str = "Checking"):
        return create_ledger_account(
            self.ledger.uuid,
            CreateAccountRequest(name=name, note="Daily account", currency_uuid=self.currency.uuid, icon="lucide:WalletCards", color_code="#405060"),
            self.request,
            self.user,
        )

    def test_create_and_get_return_the_persisted_account(self) -> None:
        created = self.create_account()

        response = get_ledger_account(self.ledger.uuid, created.uuid, self.request, self.user)

        self.assertEqual(response, created)
        self.assertEqual(response.color_code, "#405060")

    def test_create_rejects_an_unknown_currency_or_unavailable_name(self) -> None:
        self.create_account()

        with self.assertRaises(HTTPException) as missing_currency:
            create_ledger_account(
                self.ledger.uuid,
                CreateAccountRequest(name="Savings", currency_uuid=uuid4(), icon="lucide:PiggyBank", color_code="#405060"),
                self.request,
                self.user,
            )
        with self.assertRaises(HTTPException) as unavailable_name:
            self.create_account()

        self.assertEqual(missing_currency.exception.status_code, 404)
        self.assertEqual(missing_currency.exception.detail, "Currency not found")
        self.assertEqual(unavailable_name.exception.status_code, 409)
        self.assertEqual(unavailable_name.exception.detail, "Account name unavailable")

    def test_list_returns_the_entire_collection_without_page_limits(self) -> None:
        initial = list_ledger_accounts(self.ledger.uuid, self.request, self.user)
        created = [self.create_account(name) for name in ("Charlie", "Alpha", "Bravo", "Delta")]
        self.assertEqual(list_ledger_accounts(self.ledger.uuid, self.request, self.user), initial + created)

    def test_creation_limit_can_be_reused_after_deletion(self) -> None:
        initial = list_ledger_accounts(self.ledger.uuid, self.request, self.user)
        created = [self.create_account(f"Item {index}") for index in range(300 - len(initial))]
        with self.assertRaises(HTTPException) as raised:
            self.create_account("Overflow")
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, "Account limit reached")
        delete_ledger_account(self.ledger.uuid, created[-1].uuid, self.request, self.user)
        self.create_account("Replacement")
        self.assertEqual(len(list_ledger_accounts(self.ledger.uuid, self.request, self.user)), 300)

    def test_update_changes_mutable_fields_without_changing_currency(self) -> None:
        created = self.create_account()

        updated = update_ledger_account(
            self.ledger.uuid,
            created.uuid,
            UpdateAccountRequest(name="Savings", note=None, icon="lucide:PiggyBank", color_code="#010203"),
            self.request,
            self.user,
        )

        self.assertEqual(updated.name, "Savings")
        self.assertIsNone(updated.note)
        self.assertEqual(updated.currency_uuid, created.currency_uuid)
        self.assertEqual(updated.color_code, "#010203")

    def test_update_rejects_an_unknown_account_or_unavailable_name(self) -> None:
        existing = self.create_account("Existing")
        other = self.create_account("Other")
        payload = UpdateAccountRequest(name="Existing", note=None, icon="lucide:WalletCards", color_code="#405060")

        with self.assertRaises(HTTPException) as missing:
            update_ledger_account(self.ledger.uuid, uuid4(), payload, self.request, self.user)
        with self.assertRaises(HTTPException) as conflict:
            update_ledger_account(self.ledger.uuid, other.uuid, payload, self.request, self.user)

        self.assertEqual(missing.exception.status_code, 404)
        self.assertEqual(conflict.exception.status_code, 409)
        self.assertEqual(get_ledger_account(self.ledger.uuid, existing.uuid, self.request, self.user), existing)

    def test_delete_removes_an_unused_account(self) -> None:
        account = self.create_account()

        self.assertIsNone(delete_ledger_account(self.ledger.uuid, account.uuid, self.request, self.user))

        with self.assertRaises(HTTPException) as raised:
            get_ledger_account(self.ledger.uuid, account.uuid, self.request, self.user)
        self.assertEqual(raised.exception.status_code, 404)

    def test_delete_returns_conflict_when_a_movement_uses_the_account(self) -> None:
        account = self.create_account()
        with self.application.state.databases.open_ledger(f"{self.ledger.uuid}.sqlite") as unit_of_work:
            category = unit_of_work.category_repository.create("Food", "lucide:Utensils", b"\x80\x80\x80", None)
            event = unit_of_work.financial_event_repository.create(20, "Lunch", "TRANSACTION")
            unit_of_work.financial_movement_repository.create(event.uuid, account.uuid, category.uuid, -100, None)
            unit_of_work.commit()

        with self.assertRaises(HTTPException) as raised:
            delete_ledger_account(self.ledger.uuid, account.uuid, self.request, self.user)

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, "Account is in use")

    def test_another_user_cannot_discover_or_change_ledger_accounts(self) -> None:
        account = self.create_account()
        operations = (
            lambda: list_ledger_accounts(self.ledger.uuid, self.request, self.other_user),
            lambda: get_ledger_account(self.ledger.uuid, account.uuid, self.request, self.other_user),
            lambda: update_ledger_account(
                self.ledger.uuid,
                account.uuid,
                UpdateAccountRequest(name="Stolen", note=None, icon="lucide:WalletCards", color_code="#000000"),
                self.request,
                self.other_user,
            ),
            lambda: delete_ledger_account(self.ledger.uuid, account.uuid, self.request, self.other_user),
        )

        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaises(HTTPException) as raised:
                    operation()
                self.assertEqual(raised.exception.status_code, 404)
                self.assertEqual(raised.exception.detail, "Ledger not found")

    def test_request_schemas_enforce_limits_and_keep_currency_immutable(self) -> None:
        invalid_values = (
            {"name": "", "currency_uuid": self.currency.uuid, "icon": "lucide:WalletCards", "color_code": "#405060"},
            {"name": "Checking", "note": "x" * 301, "currency_uuid": self.currency.uuid, "icon": "lucide:WalletCards", "color_code": "#405060"},
            {"name": "Checking", "currency_uuid": self.currency.uuid, "icon": "WalletCards", "color_code": "#405060"},
            {"name": "Checking", "currency_uuid": self.currency.uuid, "icon": "lucide:WalletCards", "color_code": "red"},
        )
        for values in invalid_values:
            with self.subTest(values=values):
                with self.assertRaises(ValidationError):
                    CreateAccountRequest(**values)

        self.assertNotIn("currency_uuid", UpdateAccountRequest.model_fields)

    def test_routes_expose_the_complete_account_lifecycle(self) -> None:
        paths = self.application.openapi()["paths"]
        collection = paths["/api/ledgers/{ledger_uuid}/accounts"]
        member = paths["/api/ledgers/{ledger_uuid}/accounts/{account_uuid}"]

        self.assertIn("201", collection["post"]["responses"])
        self.assertIn("200", collection["get"]["responses"])
        query_parameters = [p for p in collection["get"]["parameters"] if p["in"] == "query"]
        self.assertEqual(query_parameters, [])
        self.assertIn("200", member["get"]["responses"])
        self.assertIn("200", member["put"]["responses"])
        self.assertNotIn("content", member["delete"]["responses"]["204"])
