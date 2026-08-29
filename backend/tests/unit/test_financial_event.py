"""Unit tests for the transaction-event model."""

import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.ledger.model.financial_movement import FinancialMovement
from app.domain.ledger.model.financial_event import FinancialEvent


class FinancialEventTest(unittest.TestCase):
    def test_accepts_every_supported_event_type(self) -> None:
        for event_type in ("TRANSACTION", "ACCOUNT_TRANSFER", "SHOPPING_LIST"):
            with self.subTest(event_type=event_type):
                event = FinancialEvent(
                    uuid=uuid4(),
                    occurred_at=10,
                    description="Event",
                    type=event_type,
                    movements=[],
                )
                self.assertEqual(event.type, event_type)

    def test_rejects_unknown_event_type(self) -> None:
        with self.assertRaises(ValidationError):
            FinancialEvent.model_validate(
                {
                    "uuid": uuid4(),
                    "occurred_at": 10,
                    "description": "Event",
                    "type": "UNKNOWN",
                    "movements": [],
                }
            )

    def test_rejects_description_outside_length_limits(self) -> None:
        for description in ("", "x" * 1001):
            with self.subTest(description_length=len(description)):
                with self.assertRaises(ValidationError):
                    FinancialEvent(
                        uuid=uuid4(),
                        occurred_at=10,
                        description=description,
                        type="TRANSACTION",
                        movements=[],
                    )

    def test_accepts_description_at_maximum_length(self) -> None:
        event = FinancialEvent(
            uuid=uuid4(),
            occurred_at=10,
            description="x" * 1000,
            type="TRANSACTION",
            movements=[],
        )

        self.assertEqual(len(event.description), 1000)

    def test_contains_financial_movements(self) -> None:
        event_uuid = uuid4()
        movement = FinancialMovement(
            uuid=uuid4(),
            financial_event_uuid=event_uuid,
            account_uuid=uuid4(),
            category_uuid=uuid4(),
            value=-100,
            item_name=None,
        )

        event = FinancialEvent(
            uuid=event_uuid,
            occurred_at=10,
            description="Event",
            type="TRANSACTION",
            movements=[movement],
        )

        self.assertEqual(event.movements, [movement])

    def test_requires_movements_to_be_explicitly_loaded(self) -> None:
        with self.assertRaises(ValidationError):
            FinancialEvent.model_validate(
                {
                    "uuid": uuid4(),
                    "occurred_at": 10,
                    "description": "Event",
                    "type": "TRANSACTION",
                }
            )

    def test_rejects_movement_from_another_event(self) -> None:
        with self.assertRaises(ValidationError):
            FinancialEvent(
                uuid=uuid4(),
                occurred_at=10,
                description="Event",
                type="TRANSACTION",
                movements=[
                    FinancialMovement(
                        uuid=uuid4(),
                        financial_event_uuid=uuid4(),
                        account_uuid=uuid4(),
                        category_uuid=uuid4(),
                        value=-100,
                        item_name=None,
                    )
                ],
            )


if __name__ == "__main__":
    unittest.main()
