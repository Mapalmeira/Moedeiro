"""Integration tests for the ledger SQLite financial-movement repository."""

import sqlite3
from uuid import uuid4

from pydantic import ValidationError

from app.domain.ledger.model.financial_movement import FinancialMovement
from app.infrastructure.persistence.sqlite.ledger.repository.financial_movement import SqliteFinancialMovementRepository
from tests.integration.ledger_repository_test_case import LedgerRepositoryTestCase


class SqliteFinancialMovementRepositoryTest(LedgerRepositoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repository = SqliteFinancialMovementRepository(self.connection)
        self.currency = self.create_currency()
        self.account = self.create_account(currency=self.currency)
        self.category = self.create_category()
        self.event = self.create_event()

    def create_movement(self, value: int = -100, item_name: str | None = "Lunch") -> FinancialMovement:
        return self.repository.create(self.event.uuid, self.account.uuid, self.category.uuid, value, item_name)

    def test_create_and_get_preserve_movement_relations(self) -> None:
        """create stores the event, account and category identities supplied."""
        movement = self.create_movement()

        self.assertEqual(self.repository.get(movement.uuid), movement)
        self.assertEqual(movement.transaction_event_uuid, self.event.uuid)
        self.assertEqual(movement.account_uuid, self.account.uuid)
        self.assertEqual(movement.category_uuid, self.category.uuid)

    def test_create_requires_existing_relations(self) -> None:
        """Foreign keys reject unknown event, account and category identities."""
        relation_values = [
            (uuid4(), self.account.uuid, self.category.uuid),
            (self.event.uuid, uuid4(), self.category.uuid),
            (self.event.uuid, self.account.uuid, uuid4()),
        ]
        for event_uuid, account_uuid, category_uuid in relation_values:
            with self.subTest(event_uuid=event_uuid, account_uuid=account_uuid, category_uuid=category_uuid):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.repository.create(event_uuid, account_uuid, category_uuid, -100, None)

    def test_updates_value_item_name_and_category_but_not_account(self) -> None:
        """Mutable fields change while event and account relations remain fixed."""
        movement = self.create_movement()
        other_category = self.create_category("Dining")

        self.repository.update_value(movement.uuid, -150)
        self.repository.update_item_name(movement.uuid, None)
        self.repository.update_category(movement.uuid, other_category.uuid)

        updated = self.repository.get(movement.uuid)
        assert updated is not None
        self.assertEqual(updated.value, -150)
        self.assertIsNone(updated.item_name)
        self.assertEqual(updated.category_uuid, other_category.uuid)
        self.assertEqual(updated.account_uuid, self.account.uuid)
        self.assertEqual(updated.transaction_event_uuid, self.event.uuid)

    def test_update_item_name_validates_model_limit(self) -> None:
        """Movement item names are validated before executing an update."""
        movement = self.create_movement()

        with self.assertRaises(ValidationError):
            self.repository.update_item_name(movement.uuid, "x" * 51)

    def test_create_and_update_reject_zero_value(self) -> None:
        movement = self.create_movement()

        with self.assertRaises(ValidationError):
            self.repository.create(self.event.uuid, self.account.uuid, self.category.uuid, 0, None)
        with self.assertRaises(ValidationError):
            self.repository.update_value(movement.uuid, 0)

    def test_list_by_transaction_event_excludes_other_events(self) -> None:
        """The relation-specific listing only returns movements from one event."""
        first = self.create_movement(-100)
        other_event = self.create_event("Other")
        self.repository.create(other_event.uuid, self.account.uuid, self.category.uuid, 50, None)

        movements = self.repository.list_by_transaction_event(self.event.uuid)

        self.assertEqual(movements, [first])

    def test_list_page_orders_and_rejects_all_uuid_sorting(self) -> None:
        """Movement pagination exposes values but no entity or relation UUID."""
        for value in (30, 10, 20):
            self.create_movement(value, None)

        page = self.repository.list_page(1, 2, "value", True)

        self.assertEqual([movement.value for movement in page], [10, 20])
        for sort_key in ("uuid", "transaction_event_uuid", "account_uuid", "category_uuid"):
            with self.subTest(sort_key=sort_key):
                with self.assertRaises(ValueError):
                    self.repository.list_page(1, 10, sort_key, True)

    def test_repository_does_not_commit_its_changes(self) -> None:
        """Rolling back removes the movement but preserves committed relations."""
        self.connection.commit()
        self.create_movement()

        self.connection.rollback()

        self.assertEqual(self.repository.list_all(), [])


if __name__ == "__main__":
    import unittest

    unittest.main()
