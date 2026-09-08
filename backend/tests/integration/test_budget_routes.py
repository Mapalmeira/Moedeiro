from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException, Request
from pydantic import ValidationError

from app.api.ledger.routes.account import create_ledger_account
from app.api.ledger.routes.budget import (
    create_ledger_budget,
    delete_ledger_budget,
    get_ledger_budget,
    list_ledger_currency_budget_overview,
    list_ledger_budget_overview,
    update_ledger_budget,
)
from app.api.ledger.routes.category import create_ledger_category
from app.api.ledger.routes.currency import create_ledger_currency
from app.api.ledger.schema.account import CreateAccountRequest
from app.api.ledger.schema.budget import CreateBudgetRequest, UpdateBudgetRequest
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

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def payload(self, name: str = "Monthly", *, account_uuid=None, from_timestamp: int = 10, to_timestamp: int = 20, amount: int = 100) -> CreateBudgetRequest:
        return CreateBudgetRequest(
            account_uuid=account_uuid or self.account.uuid,
            category_uuid=self.category.uuid,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            name=name,
            description="Monthly spending",
            amount=amount,
        )

    def create_budget(self, name: str = "Monthly", **changes):
        return create_ledger_budget(self.ledger.uuid, self.payload(name, **changes), self.request, self.user)

    def add_spending(self, occurred_at: int, amount: int, *, account_uuid=None, category_uuid=None, quantity: int = 1) -> None:
        with self.application.state.databases.open_ledger(f"{self.ledger.uuid}.sqlite") as unit_of_work:
            event = unit_of_work.financial_event_repository.create(occurred_at, f"Spend {amount}", "TRANSACTION")
            unit_of_work.financial_movement_repository.create(
                event.uuid,
                account_uuid or self.account.uuid,
                category_uuid or self.category.uuid,
                -amount,
                None,
                quantity,
            )
            unit_of_work.commit()

    def test_create_and_get_use_one_account_and_derive_currency_outside_the_budget(self) -> None:
        created = self.create_budget()
        response = get_ledger_budget(self.ledger.uuid, created.uuid, self.request, self.user)

        self.assertEqual(response, created)
        self.assertEqual(response.account_uuid, self.account.uuid)
        self.assertNotIn("currency_uuid", response.model_fields)
        self.assertNotIn("account_uuids", response.model_fields)

    def test_create_maps_limit_relations_and_duplicate_name(self) -> None:
        with self.assertRaises(HTTPException) as account_error:
            create_ledger_budget(self.ledger.uuid, self.payload(account_uuid=uuid4()), self.request, self.user)
        with self.assertRaises(HTTPException) as category_error:
            create_ledger_budget(self.ledger.uuid, self.payload().model_copy(update={"category_uuid": uuid4()}), self.request, self.user)
        self.create_budget("Existing")
        with self.assertRaises(HTTPException) as name_error:
            self.create_budget("Existing")
        with patch("app.application.ledger.use_cases.budget.MAXIMUM_BUDGETS", 1):
            with self.assertRaises(HTTPException) as limit_error:
                self.create_budget("Overflow")

        self.assertEqual((account_error.exception.status_code, account_error.exception.detail), (404, "Account not found"))
        self.assertEqual((category_error.exception.status_code, category_error.exception.detail), (404, "Category not found"))
        self.assertEqual((name_error.exception.status_code, name_error.exception.detail), (409, "Budget name unavailable"))
        self.assertEqual((limit_error.exception.status_code, limit_error.exception.detail), (409, "Budget limit reached"))

    def test_update_changes_mutable_fields_and_preserves_account(self) -> None:
        created = self.create_budget()
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
            ),
            self.request,
            self.user,
        )

        self.assertEqual(updated.account_uuid, created.account_uuid)
        self.assertEqual(updated.category_uuid, self.other_category.uuid)
        self.assertEqual(updated.name, "Updated")
        self.assertNotIn("account_uuid", UpdateBudgetRequest.model_fields)
        self.assertNotIn("currency_uuid", UpdateBudgetRequest.model_fields)

    def test_overview_classifies_and_evaluates_only_budgets_that_started(self) -> None:
        finished = self.create_budget("Finished", from_timestamp=1, to_timestamp=10)
        active = self.create_budget("Active", from_timestamp=10, to_timestamp=30)
        future = self.create_budget("Future", from_timestamp=30, to_timestamp=40)
        self.add_spending(5, 20)
        self.add_spending(15, 30)

        with patch("app.api.ledger.routes.budget.time.time", return_value=20):
            page = list_ledger_budget_overview(self.ledger.uuid, self.request, self.user, 3)

        by_uuid = {item.uuid: item for item in page.items}
        self.assertEqual(by_uuid[finished.uuid].state, "FINISHED")
        self.assertEqual(by_uuid[finished.uuid].spent_amount, 20)
        self.assertTrue(by_uuid[finished.uuid].fulfilled)
        self.assertEqual(by_uuid[active.uuid].state, "ACTIVE")
        self.assertEqual(by_uuid[active.uuid].spent_amount, 30)
        self.assertIsNone(by_uuid[future.uuid].spent_amount)

    def test_overview_filters_states_search_and_uses_cursor(self) -> None:
        self.create_budget("Alpha", from_timestamp=10, to_timestamp=30)
        self.create_budget("Bravo", from_timestamp=10, to_timestamp=30)
        self.create_budget("Future", from_timestamp=30, to_timestamp=40)

        with patch("app.api.ledger.routes.budget.time.time", return_value=20):
            first = list_ledger_budget_overview(self.ledger.uuid, self.request, self.user, 1, ["ACTIVE"], search="a")
            second = list_ledger_budget_overview(self.ledger.uuid, self.request, self.user, 1, ["ACTIVE"], cursor=first.next_cursor)

        self.assertEqual([item.name for item in first.items], ["Alpha"])
        self.assertEqual([item.name for item in second.items], ["Bravo"])

    def test_overview_rejects_unknown_relations_and_currency_overview_rejects_unknown_currency(self) -> None:
        missing = uuid4()
        with patch("app.api.ledger.routes.budget.time.time", return_value=20):
            with self.assertRaises(HTTPException) as overview_error:
                list_ledger_budget_overview(self.ledger.uuid, self.request, self.user, 1, None, missing)
            with self.assertRaises(HTTPException) as category_error:
                list_ledger_budget_overview(self.ledger.uuid, self.request, self.user, 1, category_uuid=missing)
            with self.assertRaises(HTTPException) as currency_error:
                list_ledger_currency_budget_overview(self.ledger.uuid, missing, self.request, self.user, 1)

        self.assertEqual((overview_error.exception.status_code, overview_error.exception.detail), (404, "Account not found"))
        self.assertEqual((category_error.exception.status_code, category_error.exception.detail), (404, "Category not found"))
        self.assertEqual((currency_error.exception.status_code, currency_error.exception.detail), (404, "Currency not found"))

    def test_currency_overview_returns_the_active_budgets_with_highest_usage_first(self) -> None:
        over = self.create_budget("Over", amount=100, from_timestamp=10, to_timestamp=40)
        lower = self.create_budget("Lower", amount=200, from_timestamp=10, to_timestamp=35)
        self.create_budget("Future", from_timestamp=30, to_timestamp=40)
        self.add_spending(15, 120)

        with patch("app.api.ledger.routes.budget.time.time", return_value=20):
            items = list_ledger_currency_budget_overview(self.ledger.uuid, self.currency.uuid, self.request, self.user, 2)

        self.assertEqual([item.uuid for item in items], [over.uuid, lower.uuid])
        self.assertEqual([item.spent_amount for item in items], [120, 120])

    def test_page_size_and_invalid_cursor_are_rejected(self) -> None:
        with self.assertRaises(HTTPException) as page_error:
            list_ledger_budget_overview(self.ledger.uuid, self.request, self.user, 4)
        with self.assertRaises(HTTPException) as cursor_error:
            list_ledger_budget_overview(self.ledger.uuid, self.request, self.user, 1, cursor="not-a-cursor")

        self.assertEqual(page_error.exception.status_code, 422)
        self.assertEqual(cursor_error.exception.status_code, 422)
        self.assertEqual(cursor_error.exception.detail, "Invalid cursor")

    def test_delete_and_missing_budget_map_to_not_found(self) -> None:
        created = self.create_budget()
        self.assertIsNone(delete_ledger_budget(self.ledger.uuid, created.uuid, self.request, self.user))
        with self.assertRaises(HTTPException) as raised:
            get_ledger_budget(self.ledger.uuid, created.uuid, self.request, self.user)
        self.assertEqual((raised.exception.status_code, raised.exception.detail), (404, "Budget not found"))

    def test_request_schemas_enforce_budget_limits_and_allow_zero(self) -> None:
        self.assertEqual(self.payload(amount=0).amount, 0)
        payload_without_description = self.payload().model_dump()
        payload_without_description.pop("description")
        self.assertIsNone(CreateBudgetRequest(**payload_without_description).description)
        self.assertEqual(CreateBudgetRequest(**{**payload_without_description, "description": ""}).description, "")
        invalid_values = (
            {**self.payload().model_dump(), "name": ""},
            {**self.payload().model_dump(), "amount": -1},
            {**self.payload().model_dump(), "from_timestamp": 20, "to_timestamp": 20},
        )
        for values in invalid_values:
            with self.subTest(values=values):
                with self.assertRaises(ValidationError):
                    CreateBudgetRequest(**values)

    def test_openapi_exposes_overview_and_currency_overview_before_budget_identifier(self) -> None:
        paths = self.application.openapi()["paths"]
        self.assertIn("/api/ledgers/{ledger_uuid}/budgets/overview", paths)
        self.assertIn("/api/ledgers/{ledger_uuid}/budgets/currency-overview", paths)
        self.assertIn("/api/ledgers/{ledger_uuid}/budgets/{budget_uuid}", paths)
        self.assertIn("get", paths["/api/ledgers/{ledger_uuid}/budgets/overview"])
        self.assertIn("get", paths["/api/ledgers/{ledger_uuid}/budgets/currency-overview"])


if __name__ == "__main__":
    unittest.main()
