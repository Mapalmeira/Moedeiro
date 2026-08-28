"""Unit tests for the financial-movement model."""

import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.ledger.model.financial_movement import FinancialMovement


class FinancialMovementTest(unittest.TestCase):
    def test_accepts_positive_negative_and_zero_values(self) -> None:
        for value in (-100, 0, 100):
            with self.subTest(value=value):
                movement = FinancialMovement(
                    uuid=uuid4(),
                    transaction_event_uuid=uuid4(),
                    account_uuid=uuid4(),
                    category_uuid=uuid4(),
                    value=value,
                )
                self.assertEqual(movement.value, value)

    def test_accepts_optional_item_name(self) -> None:
        movement = FinancialMovement(
            uuid=uuid4(),
            transaction_event_uuid=uuid4(),
            account_uuid=uuid4(),
            category_uuid=uuid4(),
            value=-100,
        )

        self.assertIsNone(movement.item_name)

    def test_rejects_item_name_longer_than_limit(self) -> None:
        with self.assertRaises(ValidationError):
            FinancialMovement(
                uuid=uuid4(),
                transaction_event_uuid=uuid4(),
                account_uuid=uuid4(),
                category_uuid=uuid4(),
                value=-100,
                item_name="x" * 31,
            )


if __name__ == "__main__":
    unittest.main()
