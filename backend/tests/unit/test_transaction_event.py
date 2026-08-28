"""Unit tests for the transaction-event model."""

import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.ledger.model.transaction_event import TransactionEvent


class TransactionEventTest(unittest.TestCase):
    def test_accepts_every_supported_event_type(self) -> None:
        for event_type in ("TRANSACTION", "ACCOUNT_TRANSFER", "SHOPPING_LIST"):
            with self.subTest(event_type=event_type):
                event = TransactionEvent(
                    uuid=uuid4(),
                    occurred_at=10,
                    description="Event",
                    type=event_type,
                )
                self.assertEqual(event.type, event_type)

    def test_rejects_unknown_event_type(self) -> None:
        with self.assertRaises(ValidationError):
            TransactionEvent.model_validate(
                {
                    "uuid": uuid4(),
                    "occurred_at": 10,
                    "description": "Event",
                    "type": "UNKNOWN",
                }
            )

    def test_rejects_description_outside_length_limits(self) -> None:
        for description in ("", "x" * 301):
            with self.subTest(description_length=len(description)):
                with self.assertRaises(ValidationError):
                    TransactionEvent(
                        uuid=uuid4(),
                        occurred_at=10,
                        description=description,
                        type="TRANSACTION",
                    )


if __name__ == "__main__":
    unittest.main()
