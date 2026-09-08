"""Unit tests for the budget model."""

import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.ledger.model.budget import Budget


class BudgetTest(unittest.TestCase):
    def values(self, **changes):
        values = {
            "uuid": uuid4(),
            "account_uuid": uuid4(),
            "category_uuid": uuid4(),
            "from_timestamp": 10,
            "to_timestamp": 20,
            "name": "Monthly",
            "description": "Monthly spending",
            "amount": 0,
        }
        values.update(changes)
        return values

    def test_accepts_one_account_valid_period_and_zero_amount(self) -> None:
        account_uuid = uuid4()
        budget = Budget(**self.values(account_uuid=account_uuid))

        self.assertEqual(budget.account_uuid, account_uuid)
        self.assertEqual(budget.amount, 0)

    def test_rejects_empty_or_reversed_period(self) -> None:
        for from_timestamp, to_timestamp in ((10, 10), (20, 10)):
            with self.subTest(from_timestamp=from_timestamp, to_timestamp=to_timestamp):
                with self.assertRaises(ValidationError):
                    Budget(**self.values(from_timestamp=from_timestamp, to_timestamp=to_timestamp))

    def test_rejects_negative_amount(self) -> None:
        with self.assertRaises(ValidationError):
            Budget(**self.values(amount=-1))

    def test_rejects_name_outside_length_limits(self) -> None:
        for name in ("", "x" * 51):
            with self.subTest(name_length=len(name)):
                with self.assertRaises(ValidationError):
                    Budget(**self.values(name=name))

    def test_accepts_name_at_maximum_length(self) -> None:
        budget = Budget(**self.values(name="x" * 50))
        self.assertEqual(len(budget.name), 50)

    def test_description_is_optional_and_accepts_empty_text(self) -> None:
        self.assertIsNone(Budget(**{key: value for key, value in self.values().items() if key != "description"}).description)
        self.assertEqual(Budget(**self.values(description="")).description, "")

    def test_rejects_description_above_maximum_length(self) -> None:
        with self.assertRaises(ValidationError):
            Budget(**self.values(description="x" * 301))


if __name__ == "__main__":
    unittest.main()
