"""Integration tests for cash-flow SQLite queries."""

from app.domain.ledger.model.account import Account
from app.domain.ledger.model.transaction_event import TransactionEvent, TransactionEventType
from app.domain.ledger.model.transaction_event_filter import TransactionEventFilter
from app.infrastructure.persistence.sqlite.ledger.repository.financial_movement import SqliteFinancialMovementRepository
from app.infrastructure.persistence.sqlite.ledger.repository.transaction_event import SqliteTransactionEventRepository
from app.infrastructure.persistence.sqlite.ledger.repository.cash_flow_query import SqliteCashFlowQueryRepository
from tests.integration.ledger_repository_test_case import LedgerRepositoryTestCase


class SqliteCashFlowQueryRepositoryTest(LedgerRepositoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repository = SqliteCashFlowQueryRepository(self.connection)
        self.event_repository = SqliteTransactionEventRepository(self.connection)
        self.movement_repository = SqliteFinancialMovementRepository(self.connection)
        self.currency = self.create_currency()
        self.other_currency = self.create_currency("Dollar")
        self.account = self.create_account(currency=self.currency)
        self.other_account = self.create_account("Other real account", self.currency)
        self.foreign_currency_account = self.create_account("Dollar account", self.other_currency)
        self.category = self.create_category()

    def add_movement(self, description: str, occurred_at: int, value: int, account: Account | None = None, event_type: TransactionEventType = "TRANSACTION") -> TransactionEvent:
        event = self.create_event(description, event_type, occurred_at)
        self.movement_repository.create(event.uuid, (account or self.account).uuid, self.category.uuid, value, None)
        return event

    def test_get_summary_aggregates_income_expense_and_counts_for_one_currency(self) -> None:
        """Amounts and counters exclude transfers, other currencies and the upper boundary."""
        income_event = self.add_movement("Income", 100, 100)
        self.movement_repository.create(income_event.uuid, self.account.uuid, self.category.uuid, -30, None)
        self.add_movement("Expense", 200, -20)
        transfer = self.create_event("Transfer", "ACCOUNT_TRANSFER", 250)
        self.movement_repository.create(transfer.uuid, self.account.uuid, self.category.uuid, -50, None)
        self.movement_repository.create(transfer.uuid, self.other_account.uuid, self.category.uuid, 50, None)
        self.add_movement("Other currency", 250, 1000, self.foreign_currency_account)
        self.add_movement("Upper boundary", 300, 500)

        summary = self.repository.get_summary(
            self.currency.uuid,
            TransactionEventFilter(from_timestamp=50, to_timestamp=300),
        )

        assert summary is not None
        self.assertEqual(summary.currency_uuid, self.currency.uuid)
        self.assertEqual(summary.from_timestamp, 50)
        self.assertEqual(summary.to_timestamp, 300)
        self.assertEqual(summary.income, 100)
        self.assertEqual(summary.expense, 50)
        self.assertEqual(summary.event_count, 2)
        self.assertEqual(summary.income_movement_count, 1)
        self.assertEqual(summary.expense_movement_count, 2)

    def test_get_summary_derives_missing_bounds_from_matching_events(self) -> None:
        """Absent filter bounds become the first and last represented event timestamps."""
        self.add_movement("First", 100, 50)
        self.add_movement("Last", 200, -20)
        self.add_movement("Other currency", 300, 1000, self.foreign_currency_account)

        summary = self.repository.get_summary(self.currency.uuid, TransactionEventFilter())

        assert summary is not None
        self.assertEqual(summary.from_timestamp, 100)
        self.assertEqual(summary.to_timestamp, 200)

    def test_get_summary_returns_zero_for_empty_fixed_interval_and_none_without_bounds(self) -> None:
        """A defined interval can represent zero flow; an unbounded empty result has no range."""
        fixed = self.repository.get_summary(
            self.currency.uuid,
            TransactionEventFilter(from_timestamp=10, to_timestamp=20),
        )
        unbounded = self.repository.get_summary(self.currency.uuid, TransactionEventFilter())

        assert fixed is not None
        self.assertEqual(fixed.income, 0)
        self.assertEqual(fixed.expense, 0)
        self.assertEqual(fixed.event_count, 0)
        self.assertIsNone(unbounded)

    def test_get_summary_applies_event_filters_before_aggregation(self) -> None:
        """Account and category may select an event through different movements."""
        selected_account = self.account
        selected_category = self.create_category("Selected category")
        other_category = self.create_category("Other category")
        expected = self.create_event("Expected", occurred_at=100)
        excluded = self.create_event("Excluded", occurred_at=100)
        self.movement_repository.create(expected.uuid, selected_account.uuid, other_category.uuid, 100, None)
        self.movement_repository.create(expected.uuid, self.other_account.uuid, selected_category.uuid, -40, None)
        self.movement_repository.create(excluded.uuid, self.other_account.uuid, selected_category.uuid, -500, None)

        summary = self.repository.get_summary(
            self.currency.uuid,
            TransactionEventFilter(account_uuid=selected_account.uuid, category_uuids={selected_category.uuid}),
        )

        assert summary is not None
        self.assertEqual(summary.income, 100)
        self.assertEqual(summary.expense, 40)
        self.assertEqual(summary.event_count, 1)

    def test_list_points_groups_flow_by_utc_day_and_orders_it(self) -> None:
        """Each returned point covers one complete Unix UTC day in chronological order."""
        self.add_movement("Second day", 86400 + 100, -20)
        self.add_movement("First day income", 100, 50)
        self.add_movement("First day expense", 200, -10)

        points = self.repository.list_points(self.currency.uuid, TransactionEventFilter())

        self.assertEqual([point.from_timestamp for point in points], [0, 86400])
        self.assertEqual([point.to_timestamp for point in points], [86400, 172800])
        self.assertEqual(points[0].income, 50)
        self.assertEqual(points[0].expense, 10)
        self.assertEqual(points[0].event_count, 2)
        self.assertEqual(points[1].income, 0)
        self.assertEqual(points[1].expense, 20)


if __name__ == "__main__":
    import unittest

    unittest.main()
