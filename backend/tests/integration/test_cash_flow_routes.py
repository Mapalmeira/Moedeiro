from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from fastapi import HTTPException, Request

from app.api.ledger.routes.account import create_ledger_account
from app.api.ledger.routes.cash_flow import get_ledger_cash_flow, list_ledger_cash_flow_points
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


class CashFlowRoutesTest(unittest.TestCase):
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

    def add_movement(self, occurred_at: int, value: int, quantity: int = 1) -> None:
        with self.application.state.databases.open_ledger(f"{self.ledger.uuid}.sqlite") as unit_of_work:
            event = unit_of_work.financial_event_repository.create(occurred_at, "Movement", "TRANSACTION")
            unit_of_work.financial_movement_repository.create(event.uuid, self.account.uuid, self.category.uuid, value, None, quantity)
            unit_of_work.commit()

    def test_summary_and_points_apply_the_same_filters(self) -> None:
        self.add_movement(100, 50, 2)
        self.add_movement(250, -20, 3)

        summary = get_ledger_cash_flow(self.ledger.uuid, self.currency.uuid, 100, 300, self.request, self.user, self.account.uuid, self.category.uuid, "TRANSACTION")
        points = list_ledger_cash_flow_points(self.ledger.uuid, self.currency.uuid, 100, 300, 150, self.request, self.user, self.account.uuid, self.category.uuid, "TRANSACTION")

        self.assertEqual((summary.income, summary.expense), (100, 60))
        self.assertEqual([(point.income, point.expense) for point in points], [(100, 0), (0, 60)])

    def test_queries_map_unknown_currency_account_and_category(self) -> None:
        operations = (
            ("Currency not found", lambda: get_ledger_cash_flow(self.ledger.uuid, uuid4(), 0, 10, self.request, self.user)),
            ("Account not found", lambda: get_ledger_cash_flow(self.ledger.uuid, self.currency.uuid, 0, 10, self.request, self.user, uuid4())),
            ("Category not found", lambda: get_ledger_cash_flow(self.ledger.uuid, self.currency.uuid, 0, 10, self.request, self.user, None, uuid4())),
        )

        for expected_detail, operation in operations:
            with self.subTest(expected_detail=expected_detail):
                with self.assertRaises(HTTPException) as raised:
                    operation()
                self.assertEqual(raised.exception.status_code, 404)
                self.assertEqual(raised.exception.detail, expected_detail)

    def test_queries_reject_invalid_period_and_too_many_points(self) -> None:
        with self.assertRaises(HTTPException) as invalid_period:
            get_ledger_cash_flow(self.ledger.uuid, self.currency.uuid, 10, 10, self.request, self.user)
        with self.assertRaises(HTTPException) as too_many_points:
            list_ledger_cash_flow_points(self.ledger.uuid, self.currency.uuid, 0, 301, 100, self.request, self.user)

        self.assertEqual(invalid_period.exception.status_code, 422)
        self.assertEqual(too_many_points.exception.status_code, 422)
        self.assertEqual(too_many_points.exception.detail, "Point count cannot exceed 2")

    def test_another_user_cannot_query_cash_flow(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            get_ledger_cash_flow(self.ledger.uuid, self.currency.uuid, 0, 10, self.request, self.other_user)

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(raised.exception.detail, "Ledger not found")

    def test_routes_expose_summary_and_point_queries(self) -> None:
        paths = self.application.openapi()["paths"]

        self.assertIn("200", paths["/api/ledgers/{ledger_uuid}/cash-flow"]["get"]["responses"])
        points = paths["/api/ledgers/{ledger_uuid}/cash-flow/points"]["get"]
        self.assertIn("200", points["responses"])
        point_width = next(parameter for parameter in points["parameters"] if parameter["name"] == "point_width")
        self.assertEqual(point_width["schema"]["minimum"], 1)


if __name__ == "__main__":
    unittest.main()
