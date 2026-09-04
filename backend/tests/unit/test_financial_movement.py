"""Unit tests for the financial-movement model."""

import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.ledger.model.financial_movement import FinancialMovement


class FinancialMovementTest(unittest.TestCase):
    def test_accepts_positive_and_negative_values(self) -> None:
        for value in (-100, 100):
            with self.subTest(value=value):
                movement = FinancialMovement(
                    uuid=uuid4(),
                    financial_event_uuid=uuid4(),
                    account_uuid=uuid4(),
                    category_uuid=uuid4(),
                    value=value,
                )
                self.assertEqual(movement.value, value)

    def test_rejects_zero_value(self) -> None:
        with self.assertRaises(ValidationError):
            FinancialMovement(
                uuid=uuid4(),
                financial_event_uuid=uuid4(),
                account_uuid=uuid4(),
                category_uuid=uuid4(),
                value=0,
            )

    def test_accepts_optional_item_name(self) -> None:
        movement = FinancialMovement(
            uuid=uuid4(),
            financial_event_uuid=uuid4(),
            account_uuid=uuid4(),
            category_uuid=uuid4(),
            value=-100,
        )

        self.assertIsNone(movement.item_name)
        self.assertEqual(movement.quantity, 1)

    def test_accepts_a_positive_quantity(self) -> None:
        movement = FinancialMovement(
            uuid=uuid4(),
            financial_event_uuid=uuid4(),
            account_uuid=uuid4(),
            category_uuid=uuid4(),
            value=-100,
            quantity=3,
        )

        self.assertEqual(movement.quantity, 3)

    def test_rejects_a_nonpositive_quantity(self) -> None:
        for quantity in (0, -1):
            with self.subTest(quantity=quantity):
                with self.assertRaises(ValidationError):
                    FinancialMovement(
                        uuid=uuid4(),
                        financial_event_uuid=uuid4(),
                        account_uuid=uuid4(),
                        category_uuid=uuid4(),
                        value=-100,
                        quantity=quantity,
                    )

    def test_rejects_item_name_longer_than_limit(self) -> None:
        with self.assertRaises(ValidationError):
            FinancialMovement(
                uuid=uuid4(),
                financial_event_uuid=uuid4(),
                account_uuid=uuid4(),
                category_uuid=uuid4(),
                value=-100,
                item_name="x" * 51,
            )

    def test_accepts_item_name_at_maximum_length(self) -> None:
        movement = FinancialMovement(
            uuid=uuid4(),
            financial_event_uuid=uuid4(),
            account_uuid=uuid4(),
            category_uuid=uuid4(),
            value=-100,
            item_name="x" * 50,
        )

        self.assertEqual(len(movement.item_name or ""), 50)


if __name__ == "__main__":
    unittest.main()
