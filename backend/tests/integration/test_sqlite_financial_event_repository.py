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

    def test_list_page_orders_every_matching_event_by_timestamp(self) -> None:
        first = self.repository.create(10, "First", "TRANSACTION")
        second = self.repository.create(20, "Second", "ACCOUNT_TRANSFER")
        filters = FinancialEventFilter(from_timestamp=0, to_timestamp=30)

        ascending = self.repository.list_page(1, 200, True, filters)
        descending = self.repository.list_page(1, 200, False, filters)

        self.assertEqual(ascending, [first, second])
        self.assertEqual(descending, [second, first])

    def test_repository_does_not_commit_its_changes(self) -> None:
        """Transaction ownership remains with the unit of work."""
        self.repository.create(10, "Purchase", "TRANSACTION")

        self.connection.rollback()

        self.assertEqual(self.repository.list_page(1, 200, True, FinancialEventFilter(from_timestamp=0, to_timestamp=100)), [])

    def test_list_filtered_applies_half_open_timestamp_interval(self) -> None:
        """The lower timestamp is inclusive and the upper timestamp is exclusive."""
        self.create_event("Before", occurred_at=10)
        expected = self.create_event("Inside", occurred_at=20)
        self.create_event("Upper bound", occurred_at=30)

        events = self.repository.list_filtered(FinancialEventFilter(from_timestamp=20, to_timestamp=30), True)

        self.assertEqual(events, [expected])

    def test_list_filtered_matches_the_selected_category_and_event_type(self) -> None:
        """The selected category and type are combined with AND."""
        currency = self.create_currency()
        account = self.create_account(currency=currency)
        second_category = self.create_category("Second category")
        event = self.create_event("Expected", "SHOPPING_LIST")
        other_event = self.create_event("Other", "TRANSACTION")
        movement_repository = SqliteFinancialMovementRepository(self.connection)
        movement_repository.create(event.uuid, account.uuid, second_category.uuid, -10, None)
        movement_repository.create(other_event.uuid, account.uuid, second_category.uuid, -10, None)

        events = self.repository.list_filtered(
            FinancialEventFilter(
                from_timestamp=0,
                to_timestamp=100,
                category_uuid=second_category.uuid,
                event_type="SHOPPING_LIST",
            ),
            True,
        )

        self.assertEqual([listed_event.uuid for listed_event in events], [event.uuid])
        self.assertEqual(len(events[0].movements), 1)

    def test_account_and_category_can_match_different_movements(self) -> None:
        """Independent EXISTS clauses allow distinct movements to satisfy each relation filter."""
        currency = self.create_currency()
        selected_account = self.create_account("Selected account", currency)
        other_account = self.create_account("Other account", currency)
        selected_category = self.create_category("Selected category")
        other_category = self.create_category("Other category")
        expected = self.create_event("Expected")
        account_only = self.create_event("Account only")
        category_only = self.create_event("Category only")
        movement_repository = SqliteFinancialMovementRepository(self.connection)
        movement_repository.create(expected.uuid, selected_account.uuid, other_category.uuid, -10, None)
        movement_repository.create(expected.uuid, other_account.uuid, selected_category.uuid, -20, None)
        movement_repository.create(account_only.uuid, selected_account.uuid, other_category.uuid, -30, None)
        movement_repository.create(category_only.uuid, other_account.uuid, selected_category.uuid, -40, None)

        events = self.repository.list_filtered(
            FinancialEventFilter(
                from_timestamp=0,
                to_timestamp=100,
                account_uuid=selected_account.uuid,
                category_uuid=selected_category.uuid,
            ),
            True,
        )

        self.assertEqual([event.uuid for event in events], [expected.uuid])
        self.assertEqual(len(events[0].movements), 2)

    def test_category_filter_includes_descendant_categories(self) -> None:
        currency = self.create_currency()
        account = self.create_account(currency=currency)
        parent = self.create_category("Parent")
        child = self.create_category("Child", parent)
        grandchild = self.create_category("Grandchild", child)
        expected = self.create_event("Expected")
        self.create_event("Unrelated")
        movement_repository = SqliteFinancialMovementRepository(self.connection)
        movement_repository.create(expected.uuid, account.uuid, grandchild.uuid, -10, None)

        events = self.repository.list_filtered(
            FinancialEventFilter(from_timestamp=0, to_timestamp=100, category_uuid=parent.uuid),
            True,
        )

        self.assertEqual([event.uuid for event in events], [expected.uuid])

    def test_get_and_list_page_load_movements_in_the_event(self) -> None:
        """Rich event reads hydrate movements without one query per event."""
        currency = self.create_currency()
        account = self.create_account(currency=currency)
        category = self.create_category()
        first = self.create_event("First", occurred_at=10)
        second = self.create_event("Second", occurred_at=20)
        movement_repository = SqliteFinancialMovementRepository(self.connection)
        movement_repository.create(first.uuid, account.uuid, category.uuid, -10, "First item")
        movement_repository.create(second.uuid, account.uuid, category.uuid, -20, "Second item")

        loaded = self.repository.get(first.uuid)
        page = self.repository.list_page(1, 10, True, FinancialEventFilter(from_timestamp=0, to_timestamp=100))

        assert loaded is not None
        self.assertEqual([movement.value for movement in loaded.movements], [-10])
        self.assertEqual(
            [[movement.value for movement in event.movements] for event in page],
            [[-10], [-20]],
        )

    def test_list_page_loads_movements_with_two_queries(self) -> None:
        """Movement hydration uses one batch query regardless of page size."""
        self.create_event("First", occurred_at=10)
        self.create_event("Second", occurred_at=20)
        statements: list[str] = []
        self.connection.set_trace_callback(statements.append)

        try:
            self.repository.list_page(1, 10, True, FinancialEventFilter(from_timestamp=0, to_timestamp=100))
        finally:
            self.connection.set_trace_callback(None)

        select_statements = [statement for statement in statements if statement.lstrip().startswith("SELECT")]
        self.assertEqual(len(select_statements), 2)

    def test_list_page_filters_orders_and_paginates(self) -> None:
        """Pagination is applied after filtering and orders by timestamp."""
        self.create_event("Third", occurred_at=30)
        first = self.create_event("First", occurred_at=10)
        second = self.create_event("Second", occurred_at=20)
        self.create_event("Excluded", "ACCOUNT_TRANSFER", 15)
        filters = FinancialEventFilter(from_timestamp=0, to_timestamp=100, event_type="TRANSACTION")

        page = self.repository.list_page(1, 2, True, filters)

        self.assertEqual(page, [first, second])

    def test_list_page_can_reverse_timestamp_direction(self) -> None:
        """Event timestamp is the fixed sort field while its direction remains configurable."""
        first = self.create_event("First", occurred_at=10)
        second = self.create_event("Second", occurred_at=20)

        page = self.repository.list_page(1, 10, False, FinancialEventFilter(from_timestamp=0, to_timestamp=100))

        self.assertEqual(page, [second, first])

    def test_list_page_rejects_more_than_two_hundred_events(self) -> None:
        with self.assertRaises(ValueError):
            self.repository.list_page(1, 201, True, FinancialEventFilter(from_timestamp=0, to_timestamp=100))

    def test_list_page_uses_uuid_to_break_timestamp_ties(self) -> None:
        with patch(
            "app.infrastructure.persistence.sqlite.ledger.repository.financial_event.uuid4",
            side_effect=[UUID(int=2), UUID(int=1)],
        ):
            higher_uuid = self.create_event("Higher UUID", occurred_at=10)
            lower_uuid = self.create_event("Lower UUID", occurred_at=10)

        page = self.repository.list_page(
            1,
            10,
            True,
            FinancialEventFilter(from_timestamp=0, to_timestamp=100),
        )

        self.assertEqual(page, [lower_uuid, higher_uuid])


if __name__ == "__main__":
    import unittest

    unittest.main()
