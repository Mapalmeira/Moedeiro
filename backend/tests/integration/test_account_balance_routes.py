import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi import HTTPException, Request

from app.api.ledger.routes.account import create_ledger_account
from app.api.ledger.routes.account_balance import get_ledger_account_balance, list_ledger_account_balance_points, list_ledger_account_balances
from app.api.ledger.routes.category import create_ledger_category
from app.api.ledger.routes.currency import create_ledger_currency
from app.api.ledger.schema.account import CreateAccountRequest
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


class AccountBalanceRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        directory = Path(self.temporary_directory.name)
        self.application = create_app(
            Settings(
                registry_schema_path=REGISTRY_SCHEMA_PATH,
                ledger_schema_path=LEDGER_SCHEMA_PATH,
                registry_db_path=directory / "registry/registry.sqlite",
                ledger_dbs_dir=directory / "ledgers",
                max_query_points=2,
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
            CreateCategoryRequest(name="General", icon="lucide:Circle", color_code="#708090"),
            self.request,
            self.user,
        )
        self.account = create_ledger_account(
            self.ledger.uuid,
            CreateAccountRequest(name="Checking", currency_uuid=self.currency.uuid, icon="lucide:WalletCards", color_code="#405060"),
            self.request,
            self.user,
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def add_movement(self, occurred_at: int, value: int) -> None:
        with self.application.state.databases.open_ledger(f"{self.ledger.uuid}.sqlite") as unit_of_work:
            event = unit_of_work.financial_event_repository.create(occurred_at, "Movement", "TRANSACTION")
            unit_of_work.financial_movement_repository.create(event.uuid, self.account.uuid, self.category.uuid, value, None)
            unit_of_work.commit()

    def test_balance_and_points_return_values_for_the_requested_account(self) -> None:
        self.add_movement(50, 100)
        self.add_movement(105, -20)
        self.add_movement(115, 30)

        balance = get_ledger_account_balance(self.ledger.uuid, self.account.uuid, 110, self.request, self.user)
        points = list_ledger_account_balance_points(self.ledger.uuid, self.account.uuid, self.request, self.user, 100, 2, 10)

        self.assertEqual(balance, 80)
        self.assertEqual(points, [80, 110])

    def test_balance_list_returns_account_and_currency_balances(self) -> None:
        self.add_movement(50, 100)

        balances = list_ledger_account_balances(self.ledger.uuid, 50, self.request, self.user, self.currency.uuid, 1)

        self.assertEqual(len(balances.items), 1)
        self.assertEqual((balances.items[0].account_uuid, balances.items[0].currency_uuid, balances.items[0].balance), (self.account.uuid, self.currency.uuid, 100))
        self.assertEqual(balances.total_balance, 100)

    def test_queries_return_not_found_for_an_unknown_account(self) -> None:
        account_uuid = uuid4()

        for operation in (
            lambda: get_ledger_account_balance(self.ledger.uuid, account_uuid, 10, self.request, self.user),
            lambda: list_ledger_account_balance_points(self.ledger.uuid, account_uuid, self.request, self.user, 0, 1, 10),
        ):
            with self.subTest(operation=operation):
                with self.assertRaises(HTTPException) as raised:
                    operation()
                self.assertEqual(raised.exception.status_code, 404)
                self.assertEqual(raised.exception.detail, "Account not found")

    def test_points_enforce_the_configured_result_limit(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            list_ledger_account_balance_points(self.ledger.uuid, self.account.uuid, self.request, self.user, 0, 3, 10)

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(raised.exception.detail, "Point count cannot exceed 2")

    def test_another_user_cannot_query_the_account(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            get_ledger_account_balance(self.ledger.uuid, self.account.uuid, 10, self.request, self.other_user)

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(raised.exception.detail, "Ledger not found")

    def test_routes_expose_current_and_interval_account_balances(self) -> None:
        paths = self.application.openapi()["paths"]

        balances = paths["/api/ledgers/{ledger_uuid}/balances"]["get"]
        self.assertIn("200", balances["responses"])
        self.assertTrue(any(parameter["name"] == "limit" for parameter in balances["parameters"]))
        self.assertIn("200", paths["/api/ledgers/{ledger_uuid}/accounts/{account_uuid}/balance"]["get"]["responses"])
        points = paths["/api/ledgers/{ledger_uuid}/accounts/{account_uuid}/balance/points"]["get"]
        self.assertIn("200", points["responses"])
        point_count = next(parameter for parameter in points["parameters"] if parameter["name"] == "point_count")
        self.assertEqual(point_count["schema"]["minimum"], 1)
