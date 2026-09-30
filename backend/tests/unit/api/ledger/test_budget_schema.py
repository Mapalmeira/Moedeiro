import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.api.ledger.schema.budget import UpdateBudgetRequest


class BudgetSchemaTest(unittest.TestCase):
    def test_update_rejects_an_empty_or_reversed_period(self) -> None:
        for from_timestamp, to_timestamp in ((10, 10), (11, 10)):
            with self.subTest(from_timestamp=from_timestamp, to_timestamp=to_timestamp), self.assertRaises(ValidationError):
                UpdateBudgetRequest(
                    category_uuid=uuid4(),
                    from_timestamp=from_timestamp,
                    to_timestamp=to_timestamp,
                    name="Food",
                    amount=100,
                )
