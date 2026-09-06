from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException, Request
from pydantic import ValidationError

from app.api.ledger.routes.account import create_ledger_account
from app.api.ledger.routes.budget import create_ledger_budget, delete_ledger_budget, get_ledger_budget, get_ledger_budget_status, list_ledger_budget_statuses, list_ledger_budgets, update_ledger_budget
from app.api.ledger.routes.category import create_ledger_category
from app.api.ledger.routes.currency import create_ledger_currency
from app.api.ledger.schema.account import CreateAccountRequest
from app.api.ledger.schema.budget import CreateBudgetRequest, UpdateBudgetRequest
from app.domain.ledger.model.budget import MAX_BUDGET_ACCOUNTS
from app.api.ledger.schema.category import CreateCategoryRequest
from app.api.ledger.schema.currency import CreateCurrencyRequest
from app.api.registry.routes.ledger import create_owned_ledger
from app.api.registry.schema.ledger import CreateLedgerRequest
from app.factory import create_app
from app.settings import Settings
from tests.fakes import FakeCredentialOperationExecutor, FakePasswordHasher, FakeRateLimiter, FakeTotpAuthenticator


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class BudgetRoutesTest(unittest.TestCase):
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
        self.other_currency = create_ledger_currency(
            self.ledger.uuid,
            CreateCurrencyRequest(name="Route Dollar", prefix="$", suffix=None, decimal_places=2, icon="lucide:CircleDollarSign", color_code="#BBCCDD"),
            self.request,
            self.user,
        )
        self.category = create_ledger_category(
            self.ledger.uuid,
            CreateCategoryRequest(name="Food", icon="lucide:Utensils", color_code="#708090"),
            self.request,
            self.user,
        )
        self.other_category = create_ledger_category(
            self.ledger.uuid,
            CreateCategoryRequest(name="Leisure", icon="lucide:Gamepad2", color_code="#8090A0"),
            self.request,
            self.user,
        )
        self.account = create_ledger_account(
            self.ledger.uuid,
            CreateAccountRequest(name="Checking", currency_uuid=self.currency.uuid, icon="lucide:WalletCards", color_code="#405060"),
            self.request,
            self.user,
        )
        self.second_account = create_ledger_account(
            self.ledger.uuid,
            CreateAccountRequest(name="Savings", currency_uuid=self.currency.uuid, icon="lucide:PiggyBank", color_code="#506070"),
            self.request,
            self.user,
        )
        self.other_currency_account = create_ledger_account(
            self.ledger.uuid,
            CreateAccountRequest(name="Dollar", currency_uuid=self.other_currency.uuid, icon="lucide:WalletCards", color_code="#607080"),
            self.request,
            self.user,
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def payload(self, name: str = "Monthly", account_uuids=None) -> CreateBudgetRequest:
        return CreateBudgetRequest(
            category_uuid=self.category.uuid,
            currency_uuid=self.currency.uuid,
            from_timestamp=10,
            to_timestamp=20,
            name=name,
            description="Monthly spending",
            amount=100,
            icon="lucide:ReceiptText",
            color_code="#808080",
            account_uuids=set() if account_uuids is None else account_uuids,
        )

    def create_budget(self, name: str = "Monthly", account_uuids=None):
        return create_ledger_budget(self.ledger.uuid, self.payload(name, account_uuids), self.request, self.user)

    def test_create_and_get_return_the_budget_with_its_account_selectors(self) -> None:
        created = self.create_budget(account_uuids={self.second_account.uuid, self.account.uuid})

        response = get_ledger_budget(self.ledger.uuid, created.uuid, self.request, self.user)

        self.assertEqual(response, created)
        self.assertEqual(response.color_code, "#808080")
        self.assertEqual(response.account_uuids, sorted((self.account.uuid, self.second_account.uuid), key=lambda value: value.bytes))

    def test_create_maps_the_budget_limit(self) -> None:
        self.create_budget("First")
        with patch("app.application.ledger.use_cases.budget.MAXIMUM_BUDGETS", 1):
            with self.assertRaises(HTTPException) as raised:
                self.create_budget("Overflow")

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, "Budget limit reached")

    def test_create_maps_unknown_relations_and_currency_mismatch(self) -> None:
        payloads = (
            (404, "Currency not found", self.payload().model_copy(update={"currency_uuid": uuid4()})),
            (404, "Category not found", self.payload().model_copy(update={"category_uuid": uuid4()})),
            (404, "Account not found", self.payload().model_copy(update={"account_uuids": {uuid4()}})),
            (409, "Budget account uses a different currency", self.payload().model_copy(update={"account_uuids": {self.other_currency_account.uuid}})),
        )

        for expected_status, expected_detail, payload in payloads:
            with self.subTest(expected_detail=expected_detail):
                with self.assertRaises(HTTPException) as raised:
                    create_ledger_budget(self.ledger.uuid, payload, self.request, self.user)
                self.assertEqual(raised.exception.status_code, expected_status)
                self.assertEqual(raised.exception.detail, expected_detail)

    def test_create_and_update_map_an_unavailable_name(self) -> None:
        existing = self.create_budget("Existing")

        with self.assertRaises(HTTPException) as create_error:
            self.create_budget("Existing")
        other = self.create_budget("Other")
        update_payload = UpdateBudgetRequest(
            category_uuid=self.category.uuid,
            from_timestamp=10,
            to_timestamp=20,
            name=existing.name,
            description="Changed",
            amount=200,
            icon="lucide:Circle",
            color_code="#102030",
        )
        with self.assertRaises(HTTPException) as update_error:
            update_ledger_budget(self.ledger.uuid, other.uuid, update_payload, self.request, self.user)

        self.assertEqual(create_error.exception.status_code, 409)
        self.assertEqual(create_error.exception.detail, "Budget name unavailable")
        self.assertEqual(update_error.exception.status_code, 409)
        self.assertEqual(update_error.exception.detail, "Budget name unavailable")

    def test_list_applies_pagination_and_ordering(self) -> None:
        charlie = self.create_budget("Charlie")
        alpha = self.create_budget("Alpha")
        bravo = self.create_budget("Bravo")

        descending = list_ledger_budgets(self.ledger.uuid, self.request, self.user, 1, 3, "name", False)
        second_page = list_ledger_budgets(self.ledger.uuid, self.request, self.user, 2, 1, "name", True)

        self.assertEqual(descending, [charlie, bravo, alpha])
        self.assertEqual(second_page, [bravo])

    def test_list_rejects_a_page_larger_than_the_configured_limit(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            list_ledger_budgets(self.ledger.uuid, self.request, self.user, 1, 4, "name", True)

        self.assertEqual(raised.exception.status_code, 422)

    def test_update_changes_mutable_fields_and_account_scope_without_changing_currency(self) -> None:
        created = self.create_budget(account_uuids={self.account.uuid})

        updated = update_ledger_budget(
            self.ledger.uuid,
            created.uuid,
            UpdateBudgetRequest(
                category_uuid=self.other_category.uuid,
                from_timestamp=20,
                to_timestamp=30,
                name="Updated",
                description="Updated spending",
                amount=250,
                icon="lucide:Landmark",
                color_code="#AABBCC",
                account_uuids={self.second_account.uuid},
            ),
            self.request,
            self.user,
        )

        self.assertEqual(updated.category_uuid, self.other_category.uuid)
        self.assertEqual(updated.currency_uuid, created.currency_uuid)
        self.assertEqual(updated.account_uuids, [self.second_account.uuid])
        self.assertEqual(updated.color_code, "#AABBCC")

    def test_status_returns_spending_and_rejects_an_inactive_budget(self) -> None:
        budget = self.create_budget(account_uuids={self.account.uuid})
        with self.application.state.databases.open_ledger(f"{self.ledger.uuid}.sqlite") as unit_of_work:
            event = unit_of_work.financial_event_repository.create(15, "Groceries", "SHOPPING_LIST")
            unit_of_work.financial_movement_repository.create(event.uuid, self.account.uuid, self.category.uuid, -30, "Item", 2)
            unit_of_work.commit()

        response = get_ledger_budget_status(self.ledger.uuid, budget.uuid, 15, self.request, self.user)

        self.assertEqual(response.spent_amount, 60)
        with self.assertRaises(HTTPException) as raised:
            get_ledger_budget_status(self.ledger.uuid, budget.uuid, 20, self.request, self.user)
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, "Budget is not active at timestamp")

    def test_status_list_returns_active_budgets_with_pagination(self) -> None:
        monthly = self.create_budget("Monthly")
        alpha = self.create_budget("Alpha")

        first_page = list_ledger_budget_statuses(self.ledger.uuid, 15, self.request, self.user, 1, 1)
        second_page = list_ledger_budget_statuses(self.ledger.uuid, 15, self.request, self.user, 2, 1)

        self.assertEqual([budget_status.budget_uuid for budget_status in first_page], [alpha.uuid])
        self.assertEqual([budget_status.budget_uuid for budget_status in second_page], [monthly.uuid])

    def test_delete_removes_a_budget_and_missing_members_return_not_found(self) -> None:
        budget = self.create_budget()

        self.assertIsNone(delete_ledger_budget(self.ledger.uuid, budget.uuid, self.request, self.user))

        operations = (
            lambda: get_ledger_budget(self.ledger.uuid, budget.uuid, self.request, self.user),
            lambda: delete_ledger_budget(self.ledger.uuid, budget.uuid, self.request, self.user),
            lambda: get_ledger_budget_status(self.ledger.uuid, budget.uuid, 15, self.request, self.user),
        )
        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaises(HTTPException) as raised:
                    operation()
                self.assertEqual(raised.exception.status_code, 404)
                self.assertEqual(raised.exception.detail, "Budget not found")

    def test_another_user_cannot_discover_or_change_budgets(self) -> None:
        budget = self.create_budget()
        operations = (
            lambda: list_ledger_budgets(self.ledger.uuid, self.request, self.other_user, 1, 3, "name", True),
            lambda: get_ledger_budget(self.ledger.uuid, budget.uuid, self.request, self.other_user),
            lambda: delete_ledger_budget(self.ledger.uuid, budget.uuid, self.request, self.other_user),
        )

        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaises(HTTPException) as raised:
                    operation()
                self.assertEqual(raised.exception.status_code, 404)
                self.assertEqual(raised.exception.detail, "Ledger not found")

    def test_request_schemas_enforce_limits_and_keep_currency_immutable(self) -> None:
        invalid_values = (
            {**self.payload().model_dump(), "from_timestamp": 20, "to_timestamp": 20},
            {**self.payload().model_dump(), "name": ""},
            {**self.payload().model_dump(), "description": "x" * 301},
            {**self.payload().model_dump(), "amount": -1},
            {**self.payload().model_dump(), "icon": "ReceiptText"},
            {**self.payload().model_dump(), "color_code": "red"},
            {**self.payload().model_dump(), "account_uuids": {uuid4() for _ in range(MAX_BUDGET_ACCOUNTS + 1)}},
        )
        for values in invalid_values:
            with self.subTest(values=values):
                with self.assertRaises(ValidationError):
                    CreateBudgetRequest(**values)

        self.assertNotIn("currency_uuid", UpdateBudgetRequest.model_fields)

    def test_routes_expose_the_complete_budget_lifecycle_and_status(self) -> None:
        paths = self.application.openapi()["paths"]
        collection = paths["/api/ledgers/{ledger_uuid}/budgets"]
        statuses = paths["/api/ledgers/{ledger_uuid}/budgets/statuses"]
        member = paths["/api/ledgers/{ledger_uuid}/budgets/{budget_uuid}"]
        budget_status = paths["/api/ledgers/{ledger_uuid}/budgets/{budget_uuid}/status"]

        self.assertIn("201", collection["post"]["responses"])
        self.assertIn("200", collection["get"]["responses"])
        self.assertIn("200", statuses["get"]["responses"])
        self.assertIn("200", member["get"]["responses"])
        self.assertIn("200", member["put"]["responses"])
        self.assertNotIn("content", member["delete"]["responses"]["204"])
        self.assertIn("200", budget_status["get"]["responses"])


if __name__ == "__main__":
    unittest.main()
