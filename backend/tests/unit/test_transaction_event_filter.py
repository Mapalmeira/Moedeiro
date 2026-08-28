"""Tests for transaction-event filter validation and defaults."""

import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.ledger.model.transaction_event_filter import TransactionEventFilter


class TransactionEventFilterTest(unittest.TestCase):
    def test_accepts_all_supported_filter_dimensions(self) -> None:
        account_uuid = uuid4()
        category_uuids = {uuid4(), uuid4()}
        tag_uuids = {uuid4(), uuid4()}

        filters = TransactionEventFilter(
            from_timestamp=10,
            to_timestamp=20,
            account_uuid=account_uuid,
            category_uuids=category_uuids,
            tag_uuids=tag_uuids,
            event_types={"TRANSACTION", "SHOPPING_LIST"},
        )

        self.assertEqual(filters.account_uuid, account_uuid)
        self.assertEqual(filters.category_uuids, category_uuids)
        self.assertEqual(filters.tag_uuids, tag_uuids)
        self.assertEqual(filters.event_types, {"TRANSACTION", "SHOPPING_LIST"})

    def test_uses_empty_sets_when_multi_value_filters_are_absent(self) -> None:
        filters = TransactionEventFilter()

        self.assertEqual(filters.category_uuids, set())
        self.assertEqual(filters.tag_uuids, set())
        self.assertEqual(filters.event_types, set())

    def test_removes_duplicate_values(self) -> None:
        category_uuid = uuid4()

        filters = TransactionEventFilter.model_validate(
            {
                "category_uuids": [category_uuid, category_uuid],
                "event_types": ["TRANSACTION", "TRANSACTION"],
            }
        )

        self.assertEqual(filters.category_uuids, {category_uuid})
        self.assertEqual(filters.event_types, {"TRANSACTION"})

    def test_rejects_an_empty_or_reversed_period(self) -> None:
        for from_timestamp, to_timestamp in ((10, 10), (20, 10)):
            with self.subTest(
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
            ):
                with self.assertRaises(ValidationError):
                    TransactionEventFilter(
                        from_timestamp=from_timestamp,
                        to_timestamp=to_timestamp,
                    )

    def test_accepts_an_open_period(self) -> None:
        from_only = TransactionEventFilter(from_timestamp=10)
        to_only = TransactionEventFilter(to_timestamp=20)

        self.assertEqual(from_only.from_timestamp, 10)
        self.assertIsNone(from_only.to_timestamp)
        self.assertIsNone(to_only.from_timestamp)
        self.assertEqual(to_only.to_timestamp, 20)

    def test_rejects_unknown_event_type(self) -> None:
        with self.assertRaises(ValidationError):
            TransactionEventFilter.model_validate({"event_types": ["UNKNOWN"]})


if __name__ == "__main__":
    unittest.main()
