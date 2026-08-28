"""Unit tests for cash-flow query models."""

import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.ledger.model.cash_flow import CashFlow


class CashFlowTest(unittest.TestCase):
    def test_accepts_amounts_and_counts(self) -> None:
        cash_flow = CashFlow(
            currency_uuid=uuid4(),
            from_timestamp=10,
            to_timestamp=20,
            income=50,
            expense=100,
            event_count=3,
            income_movement_count=1,
            expense_movement_count=2,
        )

        self.assertEqual(cash_flow.income, 50)
        self.assertEqual(cash_flow.expense, 100)
        self.assertEqual(cash_flow.event_count, 3)
        self.assertEqual(cash_flow.income_movement_count, 1)
        self.assertEqual(cash_flow.expense_movement_count, 2)

    def test_rejects_negative_amounts_and_counts(self) -> None:
        for field in ("income", "expense", "event_count", "income_movement_count", "expense_movement_count"):
            values = {
                "currency_uuid": uuid4(),
                "from_timestamp": 10,
                "to_timestamp": 20,
                "income": 100,
                "expense": 50,
                "event_count": 2,
                "income_movement_count": 1,
                "expense_movement_count": 1,
            }
            values[field] = -1

            with self.subTest(field=field):
                with self.assertRaises(ValidationError):
                    CashFlow.model_validate(values)

    def test_accepts_equal_timestamps_for_single_event(self) -> None:
        cash_flow = CashFlow(
            currency_uuid=uuid4(),
            from_timestamp=10,
            to_timestamp=10,
            income=100,
            expense=0,
            event_count=1,
            income_movement_count=1,
            expense_movement_count=0,
        )

        self.assertEqual(cash_flow.from_timestamp, cash_flow.to_timestamp)

    def test_rejects_reversed_period(self) -> None:
        with self.assertRaises(ValidationError):
            CashFlow(
                currency_uuid=uuid4(),
                from_timestamp=20,
                to_timestamp=10,
                income=100,
                expense=0,
                event_count=1,
                income_movement_count=1,
                expense_movement_count=0,
            )


if __name__ == "__main__":
    unittest.main()
