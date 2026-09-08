from unittest.mock import patch
from uuid import UUID, uuid4

from pydantic import ValidationError

from app.domain.ledger.model.financial_event_filter import FinancialEventFilter
from app.infrastructure.persistence.sqlite.ledger.repository.financial_movement import SqliteFinancialMovementRepository
from app.infrastructure.persistence.sqlite.ledger.repository.financial_event import SqliteFinancialEventRepository
from tests.integration.ledger_repository_test_case import LedgerRepositoryTestCase


class SqliteFinancialEventRepositoryTest(LedgerRepositoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repository = SqliteFinancialEventRepository(self.connection)

    def test_create_get_and_list_all_preserve_event_fields(self) -> None:
        """Basic reads return generated identity and all supplied event data."""
        event = self.repository.create(10, "Purchase", "TRANSACTION")

        self.assertEqual(self.repository.get(event.uuid), event)
        self.assertEqual(event.occurred_at, 10)
        self.assertEqual(event.description, "Purchase")
        self.assertEqual(event.type, "TRANSACTION")
        self.assertEqual(event.movements, [])

    def test_get_returns_none_for_unknown_event(self) -> None:
        """An absent event is represented by None."""
        self.assertIsNone(self.repository.get(uuid4()))

    def test_count_tracks_persisted_events(self) -> None:
        self.assertEqual(self.repository.count(), 0)
        first = self.repository.create(10, "First", "TRANSACTION")
        self.repository.create(20, "Second", "TRANSACTION")

        self.assertEqual(self.repository.count(), 2)

        self.repository.delete(first.uuid)

        self.assertEqual(self.repository.count(), 1)

    def test_delete_cascades_to_the_event_movements(self) -> None:
        currency = self.create_currency()
        account = self.create_account(currency=currency)
        category = self.create_category()
        event = self.create_event()
        movement_repository = SqliteFinancialMovementRepository(self.connection)
        movement = movement_repository.create(event.uuid, account.uuid, category.uuid, -10, None)

        self.repository.delete(event.uuid)

        self.assertIsNone(self.repository.get(event.uuid))
        self.assertIsNone(self.repository.get(event.uuid))

    def test_updates_timestamp_and_description_without_changing_type(self) -> None:
        """Event updates preserve identity and event type."""
        event = self.create_event(type="SHOPPING_LIST")

        self.repository.update_occurred_at(event.uuid, 20)
        self.repository.update_description(event.uuid, "Groceries")

        updated = self.repository.get(event.uuid)
        assert updated is not None
        self.assertEqual(updated.occurred_at, 20)
        self.assertEqual(updated.description, "Groceries")
        self.assertEqual(updated.type, "SHOPPING_LIST")

    def test_create_and_update_validate_event_fields(self) -> None:
        """Repository writes enforce FinancialEvent constraints."""
        with self.assertRaises(ValidationError):
            self.repository.create(10, "", "TRANSACTION")

        event = self.create_event()
        with self.assertRaises(ValidationError):
            self.repository.update_description(event.uuid, "x" * 301)

    def test_list_after_orders_every_matching_event_by_timestamp(self) -> None:
        first = self.repository.create(10, "First", "TRANSACTION")
        second = self.repository.create(20, "Second", "ACCOUNT_TRANSFER")
        filters = FinancialEventFilter(from_timestamp=0, to_timestamp=30)

        ascending = self.repository.list_after(200, True, filters, None, None)
        descending = self.repository.list_after(200, False, filters, None, None)

        self.assertEqual(ascending, [first, second])
        self.assertEqual(descending, [second, first])

    def test_repository_does_not_commit_its_changes(self) -> None:
        """Transaction ownership remains with the unit of work."""
        self.repository.create(10, "Purchase", "TRANSACTION")

        self.connection.rollback()

        self.assertEqual(self.repository.list_after(200, True, FinancialEventFilter(from_timestamp=0, to_timestamp=100), None, None), [])

    def test_get_and_list_after_load_movements_in_the_event(self) -> None:
        """Rich event reads hydrate movements without one query per event."""
        currency = self.create_currency()
        account = self.create_account(currency=currency)
        category = self.create_category()
        first = self.create_event("First", occurred_at=10)
        second = self.create_event("Second", occurred_at=20)
        movement_repository = SqliteFinancialMovementRepository(self.connection)
        movement_repository.create(first.uuid, account.uuid, category.uuid, -10, "First item", 3)
        movement_repository.create(second.uuid, account.uuid, category.uuid, -20, "Second item")

        loaded = self.repository.get(first.uuid)
        page = self.repository.list_after(10, True, FinancialEventFilter(from_timestamp=0, to_timestamp=100), None, None)

        assert loaded is not None
        self.assertEqual([movement.value for movement in loaded.movements], [-10])
        self.assertEqual([movement.quantity for movement in loaded.movements], [3])
        self.assertEqual(
            [[movement.value for movement in event.movements] for event in page],
            [[-10], [-20]],
        )

    def test_list_after_loads_movements_with_two_queries(self) -> None:
        """Movement hydration uses one batch query regardless of page size."""
        self.create_event("First", occurred_at=10)
        self.create_event("Second", occurred_at=20)
        statements: list[str] = []
        self.connection.set_trace_callback(statements.append)

        try:
            self.repository.list_after(10, True, FinancialEventFilter(from_timestamp=0, to_timestamp=100), None, None)
        finally:
            self.connection.set_trace_callback(None)

        select_statements = [statement for statement in statements if statement.lstrip().startswith("SELECT")]
        self.assertEqual(len(select_statements), 2)

    def test_list_after_filters_orders_and_limits(self) -> None:
        """Pagination is applied after filtering and orders by timestamp."""
        self.create_event("Third", occurred_at=30)
        first = self.create_event("First", occurred_at=10)
        second = self.create_event("Second", occurred_at=20)
        self.create_event("Excluded", "ACCOUNT_TRANSFER", 15)
        filters = FinancialEventFilter(from_timestamp=0, to_timestamp=100, event_type="TRANSACTION")

        page = self.repository.list_after(2, True, filters, None, None)

        self.assertEqual(page, [first, second])

    def test_list_after_filters_by_currency_through_event_movements(self) -> None:
        first_currency = self.create_currency("First currency")
        second_currency = self.create_currency("Second currency")
        first_account = self.create_account("First account", first_currency)
        second_account = self.create_account("Second account", second_currency)
        category = self.create_category()
        first = self.create_event("First", occurred_at=10)
        second = self.create_event("Second", occurred_at=20)
        movement_repository = SqliteFinancialMovementRepository(self.connection)
        movement_repository.create(first.uuid, first_account.uuid, category.uuid, -10, None)
        movement_repository.create(second.uuid, second_account.uuid, category.uuid, -20, None)

        page = self.repository.list_after(
            10,
            True,
            FinancialEventFilter(from_timestamp=0, to_timestamp=100, currency_uuid=second_currency.uuid),
            None,
            None,
        )

        self.assertEqual([event.uuid for event in page], [second.uuid])

    def test_list_after_can_reverse_timestamp_direction(self) -> None:
        """Event timestamp is the fixed sort field while its direction remains configurable."""
        first = self.create_event("First", occurred_at=10)
        second = self.create_event("Second", occurred_at=20)

        page = self.repository.list_after(10, False, FinancialEventFilter(from_timestamp=0, to_timestamp=100), None, None)

        self.assertEqual(page, [second, first])

    def test_list_after_uses_uuid_to_break_timestamp_ties(self) -> None:
        with patch(
            "app.infrastructure.persistence.sqlite.ledger.repository.financial_event.uuid4",
            side_effect=[UUID(int=2), UUID(int=1)],
        ):
            higher_uuid = self.create_event("Higher UUID", occurred_at=10)
            lower_uuid = self.create_event("Lower UUID", occurred_at=10)

        page = self.repository.list_after(10, True, FinancialEventFilter(from_timestamp=0, to_timestamp=100), None, None)

        self.assertEqual(page, [lower_uuid, higher_uuid])


if __name__ == "__main__":
    import unittest

    unittest.main()
