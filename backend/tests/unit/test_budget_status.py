"""Unit tests for the budget-status query model."""

import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.ledger.model.budget_status import BudgetStatus


class BudgetStatusTest(unittest.TestCase):
    def test_accepts_exceeded_budget(self) -> None:
        status = BudgetStatus(
            budget_uuid=uuid4(),
            budgeted_amount=100,
            spent_amount=120,
            over_budget=True,
        )

        self.assertTrue(status.over_budget)

    def test_rejects_negative_budgeted_or_spent_amount(self) -> None:
        for field in ("budgeted_amount", "spent_amount"):
            values = {
                "budget_uuid": uuid4(),
                "budgeted_amount": 100,
                "spent_amount": 50,
                "over_budget": False,
            }
            values[field] = -1

            with self.subTest(field=field):
                with self.assertRaises(ValidationError):
                    BudgetStatus.model_validate(values)


if __name__ == "__main__":
    unittest.main()
