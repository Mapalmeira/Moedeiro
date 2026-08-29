import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.ledger.model.financial_event_filter import FinancialEventFilter


class FinancialEventFilterTest(unittest.TestCase):
    def test_accepts_all_supported_filter_dimensions(self) -> None:
        account_uuid = uuid4()
        category_uuid = uuid4()
        tag_uuid = uuid4()

        filters = FinancialEventFilter(
            from_timestamp=10,
            to_timestamp=20,
            account_uuid=account_uuid,
            category_uuid=category_uuid,
            tag_uuid=tag_uuid,
            event_type="TRANSACTION",
        )

        self.assertEqual(filters.account_uuid, account_uuid)
        self.assertEqual(filters.category_uuid, category_uuid)
        self.assertEqual(filters.tag_uuid, tag_uuid)
        self.assertEqual(filters.event_type, "TRANSACTION")

    def test_uses_none_when_optional_filters_are_absent(self) -> None:
        filters = FinancialEventFilter(from_timestamp=10, to_timestamp=20)

        self.assertIsNone(filters.category_uuid)
        self.assertIsNone(filters.tag_uuid)
        self.assertIsNone(filters.event_type)

    def test_rejects_multi_value_filter_fields(self) -> None:
        with self.assertRaises(ValidationError):
            FinancialEventFilter.model_validate(
                {"from_timestamp": 10, "to_timestamp": 20, "category_uuids": [uuid4()]}
            )

    def test_rejects_an_empty_or_reversed_period(self) -> None:
        for from_timestamp, to_timestamp in ((10, 10), (20, 10)):
            with self.subTest(
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
            ):
                with self.assertRaises(ValidationError):
                    FinancialEventFilter(
                        from_timestamp=from_timestamp,
                        to_timestamp=to_timestamp,
                    )

    def test_requires_both_period_boundaries(self) -> None:
        for values in ({}, {"from_timestamp": 10}, {"to_timestamp": 20}):
            with self.subTest(values=values):
                with self.assertRaises(ValidationError):
                    FinancialEventFilter.model_validate(values)

    def test_rejects_unknown_event_type(self) -> None:
        with self.assertRaises(ValidationError):
            FinancialEventFilter.model_validate(
                {"from_timestamp": 10, "to_timestamp": 20, "event_type": "UNKNOWN"}
            )


if __name__ == "__main__":
    unittest.main()
