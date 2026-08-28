"""Integration tests for the basic ledger SQLite transaction-event repository."""

from uuid import uuid4

from pydantic import ValidationError

from app.domain.ledger.model.transaction_event_filter import TransactionEventFilter
from app.infrastructure.persistence.sqlite.ledger.repository.transaction_event import SqliteTransactionEventRepository
from tests.integration.ledger_repository_test_case import LedgerRepositoryTestCase


class SqliteTransactionEventRepositoryTest(LedgerRepositoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repository = SqliteTransactionEventRepository(self.connection)

    def test_create_get_and_list_all_preserve_event_fields(self) -> None:
        """Basic reads return generated identity and all supplied event data."""
        self.repository.create(10, "Purchase", "TRANSACTION")
        event = self.repository.list_all()[0]

        self.assertEqual(self.repository.get(event.uuid), event)
        self.assertEqual(event.occurred_at, 10)
        self.assertEqual(event.description, "Purchase")
        self.assertEqual(event.type, "TRANSACTION")

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
        """Repository writes enforce TransactionEvent constraints."""
        with self.assertRaises(ValidationError):
            self.repository.create(10, "", "TRANSACTION")

        event = self.create_event()
        with self.assertRaises(ValidationError):
            self.repository.update_description(event.uuid, "x" * 301)

    def test_add_list_and_remove_tags(self) -> None:
        """Event-tag relations can be created, queried and removed."""
        event = self.create_event()
        first_tag = self.create_tag("First")
        second_tag = self.create_tag("Second")

        self.repository.add_tag(event.uuid, first_tag.uuid)
        self.repository.add_tag(event.uuid, second_tag.uuid)

        self.assertCountEqual(self.repository.list_tags(event.uuid), [first_tag, second_tag])

        self.repository.remove_tag(event.uuid, first_tag.uuid)
        self.assertEqual(self.repository.list_tags(event.uuid), [second_tag])

    def test_list_all_returns_every_event_without_promising_order(self) -> None:
        """list_all has no filter and returns the complete collection."""
        self.repository.create(10, "First", "TRANSACTION")
        self.repository.create(20, "Second", "ACCOUNT_TRANSFER")

        events = self.repository.list_all()

        self.assertCountEqual([event.description for event in events], ["First", "Second"])

    def test_repository_does_not_commit_its_changes(self) -> None:
        """Transaction ownership remains with the unit of work."""
        self.repository.create(10, "Purchase", "TRANSACTION")

        self.connection.rollback()

        self.assertEqual(self.repository.list_all(), [])

    def test_filtered_queries_are_explicitly_not_implemented(self) -> None:
        """Basic persistence does not silently approximate filtered behavior."""
        filters = TransactionEventFilter()

        with self.assertRaises(NotImplementedError):
            self.repository.list_filtered(filters)
        with self.assertRaises(NotImplementedError):
            self.repository.list_page(1, 10, "occurred_at", True, filters)


if __name__ == "__main__":
    import unittest

    unittest.main()
