"""Integration tests for account-balance SQLite queries."""

from uuid import uuid4

from app.infrastructure.persistence.sqlite.ledger.repository.account_balance_query import SqliteAccountBalanceQueryRepository
from app.infrastructure.persistence.sqlite.ledger.repository.financial_movement import SqliteFinancialMovementRepository
from tests.integration.ledger_repository_test_case import LedgerRepositoryTestCase


class SqliteAccountBalanceQueryRepositoryTest(LedgerRepositoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repository = SqliteAccountBalanceQueryRepository(self.connection)
        self.movement_repository = SqliteFinancialMovementRepository(self.connection)
        self.currency = self.create_currency()
        self.account = self.create_account(currency=self.currency)
        self.other_account = self.create_account("Other account", self.currency)
        self.category = self.create_category()

    def test_get_balance_at_sums_only_selected_account_through_timestamp(self) -> None:
        """The timestamp is inclusive and movements from other accounts are ignored."""
        previous = self.create_event("Previous", occurred_at=10)
        boundary = self.create_event("Boundary", occurred_at=20)
        future = self.create_event("Future", occurred_at=30)
        self.movement_repository.create(previous.uuid, self.account.uuid, self.category.uuid, 100, None)
        self.movement_repository.create(boundary.uuid, self.account.uuid, self.category.uuid, -30, None)
        self.movement_repository.create(future.uuid, self.account.uuid, self.category.uuid, 500, None)
        self.movement_repository.create(previous.uuid, self.other_account.uuid, self.category.uuid, 900, None)

        balance = self.repository.get_balance_at(self.account.uuid, 20)

        self.assertEqual(balance, 70)

    def test_get_balance_at_includes_account_transfers(self) -> None:
        """Transfers affect account balance even though cash-flow queries exclude them."""
        transfer = self.create_event("Transfer", "ACCOUNT_TRANSFER", 10)
        self.movement_repository.create(transfer.uuid, self.account.uuid, self.category.uuid, -40, None)
        self.movement_repository.create(transfer.uuid, self.other_account.uuid, self.category.uuid, 40, None)

        self.assertEqual(self.repository.get_balance_at(self.account.uuid, 10), -40)
        self.assertEqual(self.repository.get_balance_at(self.other_account.uuid, 10), 40)

    def test_get_balance_at_returns_zero_without_movements(self) -> None:
        """Unknown accounts and accounts without movements both have a zero aggregate."""
        self.assertEqual(self.repository.get_balance_at(self.account.uuid, 10), 0)
        self.assertEqual(self.repository.get_balance_at(uuid4(), 10), 0)

    def test_list_points_returns_closing_balance_for_every_anchored_day(self) -> None:
        """Points include empty days and accumulate the balance from before the interval."""
        from_timestamp = 100
        to_timestamp = from_timestamp + 3 * 86400
        before = self.create_event("Before", occurred_at=50)
        first_day = self.create_event("First day", occurred_at=from_timestamp)
        third_day = self.create_event("Third day", occurred_at=from_timestamp + 2 * 86400 + 10)
        upper_boundary = self.create_event("Upper boundary", occurred_at=to_timestamp)
        self.movement_repository.create(before.uuid, self.account.uuid, self.category.uuid, 100, None)
        self.movement_repository.create(first_day.uuid, self.account.uuid, self.category.uuid, -30, None)
        self.movement_repository.create(third_day.uuid, self.account.uuid, self.category.uuid, 20, None)
        self.movement_repository.create(upper_boundary.uuid, self.account.uuid, self.category.uuid, 500, None)

        points = self.repository.list_points(self.account.uuid, from_timestamp, to_timestamp)

        self.assertEqual(points, [70, 70, 90])

    def test_list_points_includes_account_transfers(self) -> None:
        """Daily closing balance follows the same transfer semantics as get_balance_at."""
        transfer = self.create_event("Transfer", "ACCOUNT_TRANSFER", 100)
        self.movement_repository.create(transfer.uuid, self.account.uuid, self.category.uuid, -40, None)

        points = self.repository.list_points(self.account.uuid, 100, 86500)

        self.assertEqual(points, [-40])

    def test_list_points_requires_complete_fixed_days(self) -> None:
        """Invalid or partial fixed-day intervals are rejected before querying."""
        for from_timestamp, to_timestamp in ((100, 100), (200, 100), (100, 200)):
            with self.subTest(from_timestamp=from_timestamp, to_timestamp=to_timestamp):
                with self.assertRaises(ValueError):
                    self.repository.list_points(self.account.uuid, from_timestamp, to_timestamp)


if __name__ == "__main__":
    import unittest

    unittest.main()
