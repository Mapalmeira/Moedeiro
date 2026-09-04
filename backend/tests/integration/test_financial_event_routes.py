from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from fastapi import HTTPException, Request
from pydantic import TypeAdapter, ValidationError

from app.api.ledger.routes.financial_event import create_ledger_financial_event, delete_ledger_financial_event, get_ledger_financial_event, list_ledger_financial_events, update_ledger_financial_event
from app.api.registry.routes.ledger import create_owned_ledger
from app.api.ledger.schema.financial_event import AccountTransferFeeRequest, AccountTransferFinancialEventRequest, CreateFinancialEventRequest, ShoppingListFinancialEventRequest, ShoppingListMovementRequest, SimpleFinancialEventRequest, UpdateAccountTransferFinancialEventRequest, UpdateFinancialEventRequest, UpdateShoppingListFinancialEventRequest, UpdateShoppingListMovementRequest, UpdateSimpleFinancialEventRequest
from app.api.registry.schema.ledger import CreateLedgerRequest
from app.factory import create_app
from app.settings import Settings
from tests.fakes import FakeCredentialOperationExecutor, FakePasswordHasher, FakeRateLimiter, FakeTotpAuthenticator


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class FinancialEventRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        directory = Path(self.temporary_directory.name)
        self.application = create_app(
            Settings(
                registry_schema_path=REGISTRY_SCHEMA_PATH,
                ledger_schema_path=LEDGER_SCHEMA_PATH,
                registry_db_path=directory / "registry/registry.sqlite",
                ledger_dbs_dir=directory / "ledgers",
                max_page_size=2,
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
        self.ledger = create_owned_ledger(CreateLedgerRequest(name="Household", icon="WalletCards", color_code="#102030"), self.request, self.user)
        with self.application.state.databases.open_ledger(f"{self.ledger.uuid}.sqlite") as unit_of_work:
            real = unit_of_work.currency_repository.create("Real", "R$", None, 2, "CircleDollarSign", b"\x10\x20\x30")
            dollar = unit_of_work.currency_repository.create("Dollar", "$", None, 2, "CircleDollarSign", b"\x20\x30\x40")
            self.source = unit_of_work.account_repository.create("Checking", None, real.uuid, "WalletCards", b"\x30\x40\x50")
            self.destination = unit_of_work.account_repository.create("Savings", None, dollar.uuid, "PiggyBank", b"\x40\x50\x60")
            self.food = unit_of_work.category_repository.create("Food", "Utensils", b"\x50\x60\x70", None)
            self.transport = unit_of_work.category_repository.create("Transport", "Bus", b"\x60\x70\x80", None)
            self.fee = unit_of_work.category_repository.create("Fees", "ReceiptText", b"\x70\x80\x90", None)
            unit_of_work.commit()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def create_simple(self, occurred_at: int = 10):
        return create_ledger_financial_event(
            self.ledger.uuid,
            SimpleFinancialEventRequest(type="TRANSACTION", occurred_at=occurred_at, description="Lunch", account_uuid=self.source.uuid, category_uuid=self.food.uuid, value=-100, quantity=2),
            self.request,
            self.user,
        )

    def test_create_simple_event_returns_one_movement(self) -> None:
        event = self.create_simple()

        self.assertEqual(event.type, "TRANSACTION")
        self.assertEqual(len(event.movements), 1)
        self.assertEqual(event.movements[0].account_uuid, self.source.uuid)
        self.assertEqual(event.movements[0].value, -100)
        self.assertEqual(event.movements[0].quantity, 2)

    def test_create_shopping_list_returns_expenses_on_the_selected_account(self) -> None:
        event = create_ledger_financial_event(
            self.ledger.uuid,
            ShoppingListFinancialEventRequest(
                type="SHOPPING_LIST",
                occurred_at=20,
                description="Groceries",
                account_uuid=self.source.uuid,
                movements=[
                    ShoppingListMovementRequest(category_uuid=self.food.uuid, value=-100, quantity=3, item_name="Rice"),
                    ShoppingListMovementRequest(category_uuid=self.transport.uuid, value=-20, item_name="Delivery"),
                ],
            ),
            self.request,
            self.user,
        )

        self.assertEqual(event.type, "SHOPPING_LIST")
        self.assertEqual({movement.account_uuid for movement in event.movements}, {self.source.uuid})
        self.assertEqual({movement.category_uuid for movement in event.movements}, {self.food.uuid, self.transport.uuid})
        self.assertEqual({movement.quantity for movement in event.movements}, {1, 3})

    def test_request_schemas_reject_shopping_lists_above_three_hundred_movements(self) -> None:
        movements = [ShoppingListMovementRequest(category_uuid=self.food.uuid, value=-10) for _ in range(301)]

        with self.assertRaises(ValidationError):
            ShoppingListFinancialEventRequest(
                type="SHOPPING_LIST",
                occurred_at=20,
                description="Too large",
                account_uuid=self.source.uuid,
                movements=movements,
            )
        with self.assertRaises(ValidationError):
            UpdateShoppingListFinancialEventRequest(
                type="SHOPPING_LIST",
                occurred_at=21,
                description="Too large",
                account_uuid=self.source.uuid,
                movements=[UpdateShoppingListMovementRequest(category_uuid=self.food.uuid, value=-10) for _ in range(301)],
            )

    def test_create_account_transfer_returns_explicit_values_and_optional_fee(self) -> None:
        event = create_ledger_financial_event(
            self.ledger.uuid,
            AccountTransferFinancialEventRequest(
                type="ACCOUNT_TRANSFER",
                occurred_at=30,
                description="Exchange",
                source_account_uuid=self.source.uuid,
                source_category_uuid=self.transport.uuid,
                source_value=-1000,
                destination_account_uuid=self.destination.uuid,
                destination_category_uuid=self.food.uuid,
                destination_value=180,
                fee=AccountTransferFeeRequest(category_uuid=self.fee.uuid, value=-5),
            ),
            self.request,
            self.user,
        )

        self.assertEqual(event.type, "ACCOUNT_TRANSFER")
        self.assertEqual({(movement.account_uuid, movement.category_uuid, movement.value) for movement in event.movements}, {
            (self.source.uuid, self.transport.uuid, -1000),
            (self.destination.uuid, self.food.uuid, 180),
            (self.destination.uuid, self.fee.uuid, -5),
        })

    def test_create_rejects_equal_transfer_accounts_or_unknown_relations(self) -> None:
        equal_accounts = AccountTransferFinancialEventRequest(
            type="ACCOUNT_TRANSFER",
            occurred_at=30,
            description="Invalid",
            source_account_uuid=self.source.uuid,
            source_category_uuid=self.transport.uuid,
            source_value=-100,
            destination_account_uuid=self.source.uuid,
            destination_category_uuid=self.food.uuid,
            destination_value=100,
        )
        unknown_category = SimpleFinancialEventRequest(type="TRANSACTION", occurred_at=10, description="Missing", account_uuid=self.source.uuid, category_uuid=uuid4(), value=-10)

        with self.assertRaises(HTTPException) as invalid:
            create_ledger_financial_event(self.ledger.uuid, equal_accounts, self.request, self.user)
        with self.assertRaises(HTTPException) as missing:
            create_ledger_financial_event(self.ledger.uuid, unknown_category, self.request, self.user)

        self.assertEqual(invalid.exception.status_code, 422)
        self.assertEqual(invalid.exception.detail, "Invalid financial event")
        self.assertEqual(missing.exception.status_code, 404)
        self.assertEqual(missing.exception.detail, "Category not found")

    def test_list_filters_orders_and_limits_pages(self) -> None:
        first = self.create_simple(10)
        second = self.create_simple(20)

        events = list_ledger_financial_events(self.ledger.uuid, self.request, self.user, 0, 30, 1, self.source.uuid, self.food.uuid, "TRANSACTION", True)
        with self.assertRaises(HTTPException) as too_large:
            list_ledger_financial_events(self.ledger.uuid, self.request, self.user, 0, 30, 3, None, None, None, False)
        with self.assertRaises(HTTPException) as invalid_period:
            list_ledger_financial_events(self.ledger.uuid, self.request, self.user, 30, 30, 2, None, None, None, False)

        self.assertEqual(events.events, [first])
        self.assertIsNotNone(events.next_cursor)
        next_page = list_ledger_financial_events(
            self.ledger.uuid,
            self.request,
            self.user,
            0,
            30,
            1,
            self.source.uuid,
            self.food.uuid,
            "TRANSACTION",
            True,
            events.next_cursor,
        )
        self.assertEqual(next_page.events, [second])
        self.assertIsNone(next_page.next_cursor)
        self.assertEqual(too_large.exception.status_code, 422)
        self.assertEqual(invalid_period.exception.status_code, 422)

    def test_get_update_and_delete_simple_event(self) -> None:
        event = self.create_simple()

        updated = update_ledger_financial_event(
            self.ledger.uuid,
            event.uuid,
            UpdateSimpleFinancialEventRequest(type="TRANSACTION", occurred_at=50, description="Dinner", account_uuid=self.destination.uuid, category_uuid=self.transport.uuid, value=200, quantity=4, item_name="Refund"),
            self.request,
            self.user,
        )

        self.assertEqual(updated.occurred_at, 50)
        self.assertEqual(updated.description, "Dinner")
        self.assertEqual(updated.type, event.type)
        self.assertEqual(updated.movements[0].uuid, event.movements[0].uuid)
        self.assertEqual(updated.movements[0].account_uuid, self.destination.uuid)
        self.assertEqual((updated.movements[0].category_uuid, updated.movements[0].value, updated.movements[0].quantity, updated.movements[0].item_name), (self.transport.uuid, 200, 4, "Refund"))
        self.assertEqual(get_ledger_financial_event(self.ledger.uuid, event.uuid, self.request, self.user), updated)
        self.assertIsNone(delete_ledger_financial_event(self.ledger.uuid, event.uuid, self.request, self.user))
        with self.assertRaises(HTTPException) as missing:
            get_ledger_financial_event(self.ledger.uuid, event.uuid, self.request, self.user)
        self.assertEqual(missing.exception.status_code, 404)

    def test_update_shopping_list_dispatches_its_own_editable_structure(self) -> None:
        event = create_ledger_financial_event(
            self.ledger.uuid,
            ShoppingListFinancialEventRequest(
                type="SHOPPING_LIST",
                occurred_at=20,
                description="Groceries",
                account_uuid=self.source.uuid,
                movements=[ShoppingListMovementRequest(category_uuid=self.food.uuid, value=-100, item_name="Rice")],
            ),
            self.request,
            self.user,
        )

        updated = update_ledger_financial_event(
            self.ledger.uuid,
            event.uuid,
            UpdateShoppingListFinancialEventRequest(
                type="SHOPPING_LIST",
                occurred_at=21,
                description="Market",
                account_uuid=self.destination.uuid,
                movements=[
                    UpdateShoppingListMovementRequest(uuid=event.movements[0].uuid, category_uuid=self.transport.uuid, value=-80, quantity=2, item_name="Delivery"),
                    UpdateShoppingListMovementRequest(category_uuid=self.food.uuid, value=-20, quantity=3, item_name="Milk"),
                ],
            ),
            self.request,
            self.user,
        )

        self.assertEqual(len(updated.movements), 2)
        self.assertEqual({movement.account_uuid for movement in updated.movements}, {self.destination.uuid})
        self.assertEqual({movement.quantity for movement in updated.movements}, {2, 3})

    def test_update_transfer_dispatches_values_categories_and_fee(self) -> None:
        event = create_ledger_financial_event(
            self.ledger.uuid,
            AccountTransferFinancialEventRequest(
                type="ACCOUNT_TRANSFER",
                occurred_at=30,
                description="Exchange",
                source_account_uuid=self.source.uuid,
                source_category_uuid=self.transport.uuid,
                source_value=-1000,
                destination_account_uuid=self.destination.uuid,
                destination_category_uuid=self.food.uuid,
                destination_value=180,
            ),
            self.request,
            self.user,
        )

        updated = update_ledger_financial_event(
            self.ledger.uuid,
            event.uuid,
            UpdateAccountTransferFinancialEventRequest(
                type="ACCOUNT_TRANSFER",
                occurred_at=31,
                description="Updated exchange",
                source_account_uuid=self.destination.uuid,
                source_category_uuid=self.food.uuid,
                source_value=-1100,
                destination_account_uuid=self.source.uuid,
                destination_category_uuid=self.transport.uuid,
                destination_value=190,
                fee=AccountTransferFeeRequest(category_uuid=self.fee.uuid, value=-5),
            ),
            self.request,
            self.user,
        )

        self.assertEqual({(movement.account_uuid, movement.category_uuid, movement.value) for movement in updated.movements}, {
            (self.destination.uuid, self.food.uuid, -1100),
            (self.source.uuid, self.transport.uuid, 190),
            (self.source.uuid, self.fee.uuid, -5),
        })
        self.assertEqual({movement.quantity for movement in updated.movements}, {1})

    def test_update_rejects_changing_the_event_type(self) -> None:
        event = self.create_simple()

        with self.assertRaises(HTTPException) as raised:
            update_ledger_financial_event(
                self.ledger.uuid,
                event.uuid,
                UpdateShoppingListFinancialEventRequest(
                    type="SHOPPING_LIST",
                    occurred_at=20,
                    description="Wrong type",
                    account_uuid=self.source.uuid,
                    movements=[UpdateShoppingListMovementRequest(category_uuid=self.food.uuid, value=-10)],
                ),
                self.request,
                self.user,
            )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, "Financial event type cannot be changed")

    def test_update_rejects_an_unknown_account(self) -> None:
        event = self.create_simple()

        with self.assertRaises(HTTPException) as raised:
            update_ledger_financial_event(
                self.ledger.uuid,
                event.uuid,
                UpdateSimpleFinancialEventRequest(type="TRANSACTION", occurred_at=20, description="Changed", account_uuid=uuid4(), category_uuid=self.food.uuid, value=-100),
                self.request,
                self.user,
            )

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(raised.exception.detail, "Account not found")

    def test_unknown_event_and_ledger_return_not_found(self) -> None:
        for operation, detail in (
            (lambda: get_ledger_financial_event(self.ledger.uuid, uuid4(), self.request, self.user), "Financial event not found"),
            (lambda: delete_ledger_financial_event(self.ledger.uuid, uuid4(), self.request, self.user), "Financial event not found"),
            (lambda: get_ledger_financial_event(uuid4(), uuid4(), self.request, self.user), "Ledger not found"),
        ):
            with self.subTest(detail=detail):
                with self.assertRaises(HTTPException) as raised:
                    operation()
                self.assertEqual(raised.exception.status_code, 404)
                self.assertEqual(raised.exception.detail, detail)

    def test_another_user_cannot_discover_or_change_events(self) -> None:
        event = self.create_simple()
        operations = (
            lambda: list_ledger_financial_events(self.ledger.uuid, self.request, self.other_user, 0, 100, 2, None, None, None, False),
            lambda: get_ledger_financial_event(self.ledger.uuid, event.uuid, self.request, self.other_user),
            lambda: update_ledger_financial_event(self.ledger.uuid, event.uuid, UpdateSimpleFinancialEventRequest(type="TRANSACTION", occurred_at=20, description="Changed", account_uuid=self.source.uuid, category_uuid=self.food.uuid, value=-100), self.request, self.other_user),
            lambda: delete_ledger_financial_event(self.ledger.uuid, event.uuid, self.request, self.other_user),
        )

        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaises(HTTPException) as raised:
                    operation()
                self.assertEqual(raised.exception.status_code, 404)
                self.assertEqual(raised.exception.detail, "Ledger not found")

    def test_creation_schema_discriminates_types_and_enforces_movement_rules(self) -> None:
        adapter = TypeAdapter(CreateFinancialEventRequest)
        invalid_payloads = (
            {"type": "TRANSACTION", "occurred_at": 10, "description": "Purchase", "account_uuid": self.source.uuid, "category_uuid": self.food.uuid, "value": 0},
            {"type": "TRANSACTION", "occurred_at": 10, "description": "Purchase", "account_uuid": self.source.uuid, "category_uuid": self.food.uuid, "value": -10, "quantity": 0},
            {"type": "SHOPPING_LIST", "occurred_at": 10, "description": "List", "account_uuid": self.source.uuid, "movements": []},
            {"type": "SHOPPING_LIST", "occurred_at": 10, "description": "List", "account_uuid": self.source.uuid, "movements": [{"category_uuid": self.food.uuid, "value": 10}]},
            {"type": "ACCOUNT_TRANSFER", "occurred_at": 10, "description": "Transfer", "source_account_uuid": self.source.uuid, "source_category_uuid": self.food.uuid, "source_value": 10, "destination_account_uuid": self.destination.uuid, "destination_category_uuid": self.transport.uuid, "destination_value": 10},
            {"type": "UNKNOWN", "occurred_at": 10, "description": "Unknown"},
        )
        for payload in invalid_payloads:
            with self.subTest(event_type=payload["type"]):
                with self.assertRaises(ValidationError):
                    adapter.validate_python(payload)

    def test_update_schema_discriminates_types_and_enforces_each_structure(self) -> None:
        adapter = TypeAdapter(UpdateFinancialEventRequest)
        invalid_payloads = (
            {"type": "TRANSACTION", "occurred_at": 10, "description": "Purchase", "account_uuid": self.source.uuid, "category_uuid": self.food.uuid, "value": 0},
            {"type": "TRANSACTION", "occurred_at": 10, "description": "Purchase", "account_uuid": self.source.uuid, "category_uuid": self.food.uuid, "value": -10, "quantity": 0},
            {"type": "SHOPPING_LIST", "occurred_at": 10, "description": "List", "account_uuid": self.source.uuid, "movements": []},
            {"type": "SHOPPING_LIST", "occurred_at": 10, "description": "List", "account_uuid": self.source.uuid, "movements": [{"category_uuid": self.food.uuid, "value": 10}]},
            {"type": "ACCOUNT_TRANSFER", "occurred_at": 10, "description": "Transfer", "source_account_uuid": self.source.uuid, "source_category_uuid": self.food.uuid, "source_value": 10, "destination_account_uuid": self.destination.uuid, "destination_category_uuid": self.transport.uuid, "destination_value": 10},
            {"type": "UNKNOWN", "occurred_at": 10, "description": "Unknown"},
        )
        for payload in invalid_payloads:
            with self.subTest(event_type=payload["type"]):
                with self.assertRaises(ValidationError):
                    adapter.validate_python(payload)

    def test_routes_expose_the_financial_event_lifecycle(self) -> None:
        paths = self.application.openapi()["paths"]
        collection = paths["/api/ledgers/{ledger_uuid}/events"]
        member = paths["/api/ledgers/{ledger_uuid}/events/{event_uuid}"]

        self.assertIn("201", collection["post"]["responses"])
        self.assertIn("200", collection["get"]["responses"])
        self.assertIn("200", member["get"]["responses"])
        self.assertIn("200", member["put"]["responses"])
        self.assertNotIn("content", member["delete"]["responses"]["204"])


if __name__ == "__main__":
    unittest.main()
