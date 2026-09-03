from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.application.ledger.exceptions import AccountNotFoundError, CategoryNotFoundError, FinancialEventNotFoundError, FinancialEventTypeMismatchError, FinancialMovementNotFoundError
from app.application.ledger.use_cases.financial_event import create_account_transfer_financial_event, create_shopping_list_financial_event, create_simple_financial_event, delete_financial_event, get_financial_event, list_financial_event_page, update_account_transfer_financial_event, update_shopping_list_financial_event, update_simple_financial_event
from app.domain.ledger.model.financial_event_filter import FinancialEventFilter
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.ledger.unit_of_work import SqliteLedgerUnitOfWork


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class FinancialEventUseCasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.database = SqliteDatabase.initialize(Path(self.temporary_directory.name) / "ledger.sqlite", SCHEMA_PATH)
        with self.open_ledger() as unit_of_work:
            unit_of_work.ledger_metadata_repository.create(uuid4(), 1, 10)
            self.real = unit_of_work.currency_repository.create("Real", "R$", None, 2, "CircleDollarSign", b"\x10\x20\x30")
            self.dollar = unit_of_work.currency_repository.create("Dollar", "$", None, 2, "CircleDollarSign", b"\x20\x30\x40")
            self.source = unit_of_work.account_repository.create("Checking", None, self.real.uuid, "WalletCards", b"\x30\x40\x50")
            self.destination = unit_of_work.account_repository.create("Savings", None, self.dollar.uuid, "PiggyBank", b"\x40\x50\x60")
            self.food = unit_of_work.category_repository.create("Food", "Utensils", b"\x50\x60\x70", None)
            self.transport = unit_of_work.category_repository.create("Transport", "Bus", b"\x60\x70\x80", None)
            self.fee = unit_of_work.category_repository.create("Fees", "ReceiptText", b"\x70\x80\x90", None)
            unit_of_work.commit()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def open_ledger(self) -> SqliteLedgerUnitOfWork:
        return SqliteLedgerUnitOfWork(self.database)

    def create_simple(self, value: int = -100, occurred_at: int = 10):
        return create_simple_financial_event(self.open_ledger, occurred_at, "Lunch", self.source.uuid, self.food.uuid, value, None)

    def test_create_simple_event_persists_exactly_one_movement(self) -> None:
        event = self.create_simple(250)

        self.assertEqual(event.type, "TRANSACTION")
        self.assertEqual(len(event.movements), 1)
        self.assertEqual(event.movements[0].account_uuid, self.source.uuid)
        self.assertEqual(event.movements[0].category_uuid, self.food.uuid)
        self.assertEqual(event.movements[0].value, 250)
        self.assertEqual(get_financial_event(self.open_ledger, event.uuid), event)

    def test_create_simple_event_rejects_zero_without_persisting_an_event(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not be zero"):
            self.create_simple(0)

        self.assertEqual(self.list_events(), [])

    def test_create_shopping_list_persists_expenses_on_one_account(self) -> None:
        event = create_shopping_list_financial_event(
            self.open_ledger,
            20,
            "Groceries",
            self.source.uuid,
            [(self.food.uuid, -100, "Rice"), (self.transport.uuid, -50, "Delivery")],
        )

        self.assertEqual(event.type, "SHOPPING_LIST")
        self.assertEqual({movement.account_uuid for movement in event.movements}, {self.source.uuid})
        self.assertEqual({movement.category_uuid for movement in event.movements}, {self.food.uuid, self.transport.uuid})
        self.assertEqual({movement.value for movement in event.movements}, {-100, -50})

    def test_create_shopping_list_rejects_empty_or_non_expense_movements(self) -> None:
        for movements in ([], [(self.food.uuid, 100, "Refund")], [(self.food.uuid, 0, None)]):
            with self.subTest(movements=movements):
                with self.assertRaises(ValueError):
                    create_shopping_list_financial_event(self.open_ledger, 20, "Groceries", self.source.uuid, movements)

        self.assertEqual(self.list_events(), [])

    def test_create_account_transfer_supports_different_currencies_and_destination_fee(self) -> None:
        event = create_account_transfer_financial_event(
            self.open_ledger,
            30,
            "Exchange",
            self.source.uuid,
            self.transport.uuid,
            -1000,
            self.destination.uuid,
            self.food.uuid,
            180,
            (self.fee.uuid, -5),
        )

        self.assertEqual(event.type, "ACCOUNT_TRANSFER")
        self.assertEqual({(movement.account_uuid, movement.category_uuid, movement.value) for movement in event.movements}, {
            (self.source.uuid, self.transport.uuid, -1000),
            (self.destination.uuid, self.fee.uuid, -5),
            (self.destination.uuid, self.food.uuid, 180),
        })

    def test_create_account_transfer_rejects_invalid_accounts_and_signs(self) -> None:
        invalid_values = (
            (self.source.uuid, -100, self.source.uuid, 100, None),
            (self.source.uuid, 100, self.destination.uuid, 100, None),
            (self.source.uuid, -100, self.destination.uuid, -100, None),
            (self.source.uuid, -100, self.destination.uuid, 100, (self.fee.uuid, 5)),
        )
        for source_account_uuid, source_value, destination_account_uuid, destination_value, fee in invalid_values:
            with self.subTest(source_value=source_value, destination_value=destination_value, fee=fee):
                with self.assertRaises(ValueError):
                    create_account_transfer_financial_event(
                        self.open_ledger,
                        30,
                        "Exchange",
                        source_account_uuid,
                        self.transport.uuid,
                        source_value,
                        destination_account_uuid,
                        self.food.uuid,
                        destination_value,
                        fee,
                    )

        self.assertEqual(self.list_events(), [])

    def test_creation_rejects_unknown_accounts_and_categories_atomically(self) -> None:
        operations = (
            lambda: create_simple_financial_event(self.open_ledger, 10, "Missing account", uuid4(), self.food.uuid, -10, None),
            lambda: create_simple_financial_event(self.open_ledger, 10, "Missing category", self.source.uuid, uuid4(), -10, None),
            lambda: create_shopping_list_financial_event(self.open_ledger, 10, "Missing item category", self.source.uuid, [(self.food.uuid, -10, None), (uuid4(), -20, None)]),
        )
        expected_errors = (AccountNotFoundError, CategoryNotFoundError, CategoryNotFoundError)

        for operation, expected_error in zip(operations, expected_errors, strict=True):
            with self.subTest(expected_error=expected_error):
                with self.assertRaises(expected_error):
                    operation()

        self.assertEqual(self.list_events(), [])

    def test_list_page_applies_filters_pagination_and_direction(self) -> None:
        first = self.create_simple(-100, 10)
        self.create_simple(-200, 20)
        transfer = create_account_transfer_financial_event(
            self.open_ledger,
            30,
            "Transfer",
            self.source.uuid,
            self.transport.uuid,
            -300,
            self.destination.uuid,
            self.food.uuid,
            50,
            None,
        )

        filters = FinancialEventFilter(from_timestamp=0, to_timestamp=40, account_uuid=self.destination.uuid)

        self.assertEqual(list_financial_event_page(self.open_ledger, 1, 1, False, filters), [transfer])
        self.assertEqual(list_financial_event_page(self.open_ledger, 1, 1, True, FinancialEventFilter(from_timestamp=0, to_timestamp=25)), [first])

    def test_update_simple_event_changes_its_editable_structure_including_account(self) -> None:
        event = self.create_simple()
        movement = event.movements[0]

        updated = update_simple_financial_event(self.open_ledger, event.uuid, 50, "Dinner", self.destination.uuid, self.transport.uuid, 250, "Refund")

        self.assertEqual(updated.occurred_at, 50)
        self.assertEqual(updated.description, "Dinner")
        self.assertEqual(updated.type, event.type)
        self.assertEqual(len(updated.movements), 1)
        self.assertEqual(updated.movements[0].uuid, movement.uuid)
        self.assertEqual(updated.movements[0].account_uuid, self.destination.uuid)
        self.assertEqual(updated.movements[0].category_uuid, self.transport.uuid)
        self.assertEqual(updated.movements[0].value, 250)
        self.assertEqual(updated.movements[0].item_name, "Refund")
        self.assertEqual(get_financial_event(self.open_ledger, event.uuid), updated)

    def test_update_shopping_list_updates_its_account_and_replaces_movements(self) -> None:
        event = create_shopping_list_financial_event(
            self.open_ledger,
            20,
            "Groceries",
            self.source.uuid,
            [(self.food.uuid, -100, "Rice"), (self.transport.uuid, -50, "Delivery")],
        )
        retained, removed = event.movements

        updated = update_shopping_list_financial_event(
            self.open_ledger,
            event.uuid,
            25,
            "Market",
            self.destination.uuid,
            [(retained.uuid, self.transport.uuid, -120, "Beans"), (None, self.food.uuid, -30, "Milk")],
        )

        self.assertEqual(updated.occurred_at, 25)
        self.assertEqual(updated.description, "Market")
        self.assertEqual(len(updated.movements), 2)
        self.assertEqual({movement.account_uuid for movement in updated.movements}, {self.destination.uuid})
        self.assertIn((retained.uuid, self.transport.uuid, -120, "Beans"), {(movement.uuid, movement.category_uuid, movement.value, movement.item_name) for movement in updated.movements})
        self.assertNotIn(removed.uuid, {movement.uuid for movement in updated.movements})
        self.assertEqual(get_financial_event(self.open_ledger, event.uuid), updated)

    def test_update_transfer_changes_accounts_and_can_add_update_then_remove_destination_fee(self) -> None:
        event = create_account_transfer_financial_event(
            self.open_ledger,
            30,
            "Exchange",
            self.source.uuid,
            self.transport.uuid,
            -1000,
            self.destination.uuid,
            self.food.uuid,
            180,
            None,
        )
        source = next(movement for movement in event.movements if movement.value < 0)
        destination = next(movement for movement in event.movements if movement.value > 0)

        with_fee = update_account_transfer_financial_event(
            self.open_ledger,
            event.uuid,
            31,
            "Updated exchange",
            self.destination.uuid,
            self.food.uuid,
            -1100,
            self.source.uuid,
            self.transport.uuid,
            190,
            (self.fee.uuid, -4),
        )

        self.assertEqual(len(with_fee.movements), 3)
        self.assertIn((source.uuid, self.destination.uuid, self.food.uuid, -1100), {(movement.uuid, movement.account_uuid, movement.category_uuid, movement.value) for movement in with_fee.movements})
        self.assertIn((destination.uuid, self.source.uuid, self.transport.uuid, 190), {(movement.uuid, movement.account_uuid, movement.category_uuid, movement.value) for movement in with_fee.movements})
        fee = next(movement for movement in with_fee.movements if movement.uuid not in {source.uuid, destination.uuid})
        self.assertEqual((fee.account_uuid, fee.category_uuid, fee.value), (self.source.uuid, self.fee.uuid, -4))

        changed_fee = update_account_transfer_financial_event(
            self.open_ledger,
            event.uuid,
            32,
            "Changed fee",
            self.destination.uuid,
            self.food.uuid,
            -1100,
            self.source.uuid,
            self.transport.uuid,
            190,
            (self.transport.uuid, -7),
        )

        self.assertIn((fee.uuid, self.source.uuid, self.transport.uuid, -7), {(movement.uuid, movement.account_uuid, movement.category_uuid, movement.value) for movement in changed_fee.movements})

        without_fee = update_account_transfer_financial_event(
            self.open_ledger,
            event.uuid,
            33,
            "No fee",
            self.destination.uuid,
            self.food.uuid,
            -1100,
            self.source.uuid,
            self.transport.uuid,
            190,
            None,
        )

        self.assertEqual(len(without_fee.movements), 2)
        self.assertNotIn(fee.uuid, {movement.uuid for movement in without_fee.movements})
        self.assertEqual(get_financial_event(self.open_ledger, event.uuid), without_fee)

    def test_update_rejects_a_payload_for_another_event_type(self) -> None:
        event = self.create_simple()

        with self.assertRaises(FinancialEventTypeMismatchError):
            update_shopping_list_financial_event(self.open_ledger, event.uuid, 20, "Wrong type", self.source.uuid, [(None, self.food.uuid, -10, None)])

        self.assertEqual(get_financial_event(self.open_ledger, event.uuid), event)

    def test_update_shopping_list_rejects_a_movement_from_another_event_atomically(self) -> None:
        event = create_shopping_list_financial_event(self.open_ledger, 20, "First", self.source.uuid, [(self.food.uuid, -100, "Rice")])
        other = create_shopping_list_financial_event(self.open_ledger, 21, "Other", self.source.uuid, [(self.food.uuid, -50, "Milk")])

        with self.assertRaises(FinancialMovementNotFoundError):
            update_shopping_list_financial_event(self.open_ledger, event.uuid, 30, "Changed", self.source.uuid, [(other.movements[0].uuid, self.transport.uuid, -1, None)])

        self.assertEqual(get_financial_event(self.open_ledger, event.uuid), event)
        self.assertEqual(get_financial_event(self.open_ledger, other.uuid), other)

    def test_update_rejects_invalid_or_unknown_events_atomically(self) -> None:
        event = self.create_simple()

        with self.assertRaises(ValidationError):
            update_simple_financial_event(self.open_ledger, event.uuid, 20, "", self.source.uuid, self.transport.uuid, -20, None)
        with self.assertRaises(AccountNotFoundError):
            update_simple_financial_event(self.open_ledger, event.uuid, 20, "Changed", uuid4(), self.transport.uuid, -20, None)
        with self.assertRaises(CategoryNotFoundError):
            update_simple_financial_event(self.open_ledger, event.uuid, 20, "Changed", self.source.uuid, uuid4(), -20, None)
        with self.assertRaises(FinancialEventNotFoundError):
            update_simple_financial_event(self.open_ledger, uuid4(), 20, "Missing", self.source.uuid, self.food.uuid, -20, None)

        self.assertEqual(get_financial_event(self.open_ledger, event.uuid), event)

    def test_delete_removes_the_event_and_its_movements(self) -> None:
        event = self.create_simple()

        self.assertIsNone(delete_financial_event(self.open_ledger, event.uuid))

        with self.assertRaises(FinancialEventNotFoundError):
            get_financial_event(self.open_ledger, event.uuid)
        with self.open_ledger() as unit_of_work:
            self.assertEqual(unit_of_work.financial_movement_repository.list_by_financial_event(event.uuid), [])

    def test_get_and_delete_reject_unknown_events(self) -> None:
        for operation in (
            lambda: get_financial_event(self.open_ledger, uuid4()),
            lambda: delete_financial_event(self.open_ledger, uuid4()),
        ):
            with self.subTest(operation=operation):
                with self.assertRaises(FinancialEventNotFoundError):
                    operation()

    def list_events(self):
        return list_financial_event_page(self.open_ledger, 1, 200, True, FinancialEventFilter(from_timestamp=0, to_timestamp=100))


if __name__ == "__main__":
    unittest.main()
