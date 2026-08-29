"""Unit tests for the budget model."""

import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.ledger.model.budget import Budget


class BudgetTest(unittest.TestCase):
    def test_accepts_valid_period_and_zero_amount(self) -> None:
        budget = Budget(
            uuid=uuid4(),
            category_uuid=uuid4(),
            currency_uuid=uuid4(),
            from_timestamp=10,
            to_timestamp=20,
            name="Monthly",
            description="Monthly spending",
            amount=0,
        )

        self.assertEqual(budget.amount, 0)

    def test_rejects_empty_or_reversed_period(self) -> None:
        for from_timestamp, to_timestamp in ((10, 10), (20, 10)):
            with self.subTest(from_timestamp=from_timestamp, to_timestamp=to_timestamp):
                with self.assertRaises(ValidationError):
                    Budget(
                        uuid=uuid4(),
                        category_uuid=uuid4(),
                        currency_uuid=uuid4(),
                        from_timestamp=from_timestamp,
                        to_timestamp=to_timestamp,
                        name="Monthly",
                        description="Monthly spending",
                        amount=100,
                    )

    def test_rejects_negative_amount(self) -> None:
        with self.assertRaises(ValidationError):
            Budget(
                uuid=uuid4(),
                category_uuid=uuid4(),
                currency_uuid=uuid4(),
                from_timestamp=10,
                to_timestamp=20,
                name="Monthly",
                description="Monthly spending",
                amount=-1,
            )

    def test_rejects_name_outside_length_limits(self) -> None:
        for name in ("", "x" * 51):
            with self.subTest(name_length=len(name)):
                with self.assertRaises(ValidationError):
                    Budget(
                        uuid=uuid4(),
                        category_uuid=uuid4(),
                        currency_uuid=uuid4(),
                        from_timestamp=10,
                        to_timestamp=20,
                        name=name,
                        description="Monthly spending",
                        amount=100,
                    )

    def test_accepts_name_at_maximum_length(self) -> None:
        budget = Budget(
            uuid=uuid4(),
            category_uuid=uuid4(),
            currency_uuid=uuid4(),
            from_timestamp=10,
            to_timestamp=20,
            name="x" * 50,
            description="Monthly spending",
            amount=100,
        )

        self.assertEqual(len(budget.name), 50)

    def test_rejects_description_outside_length_limits(self) -> None:
        for description in ("", "x" * 301):
            with self.subTest(description_length=len(description)):
                with self.assertRaises(ValidationError):
                    Budget(
                        uuid=uuid4(),
                        category_uuid=uuid4(),
                        currency_uuid=uuid4(),
                        from_timestamp=10,
                        to_timestamp=20,
                        name="Monthly",
                        description=description,
                        amount=100,
                    )


if __name__ == "__main__":
    unittest.main()
