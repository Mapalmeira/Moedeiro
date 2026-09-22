"""Integration tests for the ledger SQLite financial-movement repository."""

import sqlite3
from uuid import uuid4

from app.domain.ledger.model.financial_movement import FinancialMovement
from app.domain.ledger.model.financial_event_filter import FinancialEventFilter
from app.infrastructure.persistence.sqlite.ledger.repository.financial_event import SqliteFinancialEventRepository
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

    def create_movement(self, value: int = -100, item_name: str | None = "Lunch", quantity: int = 1) -> FinancialMovement:
        return self.repository.create(self.event.uuid, self.account.uuid, self.category.uuid, value, item_name, quantity)

    def test_create_preserves_movement_relations(self) -> None:
        """create stores the event, account and category identities supplied."""
        movement = self.create_movement(quantity=3)

        event = SqliteFinancialEventRepository(self.connection).get(self.event.uuid)
        assert event is not None
        self.assertEqual(event.movements, [movement])
        self.assertEqual(movement.financial_event_uuid, self.event.uuid)
        self.assertEqual(movement.account_uuid, self.account.uuid)
        self.assertEqual(movement.category_uuid, self.category.uuid)
        self.assertEqual(movement.quantity, 3)

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

    def test_update_changes_all_mutable_fields(self) -> None:
        movement = self.create_movement()
        other_category = self.create_category("Dining")
        other_account = self.create_account("Savings", currency=self.currency)
        updated_movement = movement.model_copy(
            update={
                "account_uuid": other_account.uuid,
                "category_uuid": other_category.uuid,
                "value": -150,
                "quantity": 2,
                "item_name": None,
                "special_type": "FEE",
            }
        )

        self.repository.update(updated_movement)

        event = SqliteFinancialEventRepository(self.connection).get(self.event.uuid)
        assert event is not None
        self.assertEqual(event.movements, [updated_movement])
        self.assertEqual(event.movements[0].special_type, "FEE")

    def test_delete_removes_only_the_selected_movement(self) -> None:
        selected = self.create_movement(-100, "Lunch")
        remaining = self.create_movement(-50, "Coffee")

        self.repository.delete(selected.uuid)

        event = SqliteFinancialEventRepository(self.connection).get(self.event.uuid)
        assert event is not None
        self.assertEqual(event.movements, [remaining])

    def test_repository_does_not_commit_its_changes(self) -> None:
        """Rolling back removes the movement but preserves committed relations."""
        self.connection.commit()
        self.create_movement()

        self.connection.rollback()

        events = SqliteFinancialEventRepository(self.connection).list_after(10, True, FinancialEventFilter(from_timestamp=0, to_timestamp=100), None, None)
        self.assertEqual(events[0].movements, [])
