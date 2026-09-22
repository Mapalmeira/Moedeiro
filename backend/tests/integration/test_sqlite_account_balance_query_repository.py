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
        self.other_currency = self.create_currency("Dollar")
        self.foreign_account = self.create_account("Foreign", self.other_currency)
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

    def test_get_balance_at_returns_zero_for_an_account_without_movements(self) -> None:
        self.assertEqual(self.repository.get_balance_at(self.account.uuid, 10), 0)

    def test_list_balances_at_returns_zero_accounts_and_can_filter_currency(self) -> None:
        event = self.create_event("Balances", occurred_at=10)
        self.movement_repository.create(event.uuid, self.account.uuid, self.category.uuid, 100, None)
        self.movement_repository.create(event.uuid, self.foreign_account.uuid, self.category.uuid, 250, None)

        all_balances = self.repository.list_balances_at(10)
        selected = self.repository.list_balances_at(10, self.currency.uuid)

        self.assertEqual(
            {(account_uuid, currency_uuid): balance for account_uuid, currency_uuid, balance in all_balances},
            {
                (self.account.uuid, self.currency.uuid): 100,
                (self.other_account.uuid, self.currency.uuid): 0,
                (self.foreign_account.uuid, self.other_currency.uuid): 250,
            },
        )
        self.assertEqual(
            [(account_uuid, currency_uuid, balance) for account_uuid, currency_uuid, balance in selected],
            [(self.account.uuid, self.currency.uuid, 100), (self.other_account.uuid, self.currency.uuid, 0)],
        )


    def test_list_balances_can_limit_accounts_before_aggregation(self) -> None:
        event = self.create_event("Balances", occurred_at=10)
        future = self.create_event("Future", occurred_at=20)
        self.movement_repository.create(event.uuid, self.account.uuid, self.category.uuid, 100, None)
        self.movement_repository.create(event.uuid, self.other_account.uuid, self.category.uuid, 200, None)
        self.movement_repository.create(future.uuid, self.account.uuid, self.category.uuid, 900, None)

        selected = self.repository.list_balances_at(10, self.currency.uuid, 1)

        self.assertEqual(selected, [(self.account.uuid, self.currency.uuid, 100)])
        self.assertEqual(self.repository.get_currency_balance_at(self.currency.uuid, 10), 300)

    def test_queries_raise_for_an_unknown_account(self) -> None:
        account_uuid = uuid4()

        with self.assertRaises(LookupError):
            self.repository.get_balance_at(account_uuid, 10)
        with self.assertRaises(LookupError):
            self.repository.list_points(account_uuid, 100, 1, 86400)

    def test_list_points_returns_closing_balance_for_every_anchored_interval(self) -> None:
        """Points include empty intervals and accumulate the prior balance."""
        from_timestamp = 100
        point_count = 3
        point_interval = 86400
        to_timestamp = from_timestamp + point_count * point_interval
        before = self.create_event("Before", occurred_at=50)
        first_day = self.create_event("First day", occurred_at=from_timestamp)
        third_day = self.create_event("Third day", occurred_at=from_timestamp + 2 * 86400 + 10)
        upper_boundary = self.create_event("Upper boundary", occurred_at=to_timestamp)
        self.movement_repository.create(before.uuid, self.account.uuid, self.category.uuid, 100, None)
        self.movement_repository.create(first_day.uuid, self.account.uuid, self.category.uuid, -30, None)
        self.movement_repository.create(third_day.uuid, self.account.uuid, self.category.uuid, 20, None)
        self.movement_repository.create(upper_boundary.uuid, self.account.uuid, self.category.uuid, 500, None)

        points = self.repository.list_points(self.account.uuid, from_timestamp, point_count, point_interval)

        self.assertEqual(points, [70, 70, 90])

    def test_list_points_includes_account_transfers(self) -> None:
        """Each point follows the same transfer semantics as get_balance_at."""
        transfer = self.create_event("Transfer", "ACCOUNT_TRANSFER", 100)
        self.movement_repository.create(transfer.uuid, self.account.uuid, self.category.uuid, -40, None)
        self.movement_repository.create(transfer.uuid, self.other_account.uuid, self.category.uuid, 40, None)

        points = self.repository.list_points(self.account.uuid, 100, 1, 86400)

        self.assertEqual(points, [-40])

    def test_list_points_uses_the_supplied_interval(self) -> None:
        before = self.create_event("Before", occurred_at=50)
        first_point = self.create_event("First point", occurred_at=109)
        second_point = self.create_event("Second point", occurred_at=110)
        self.movement_repository.create(before.uuid, self.account.uuid, self.category.uuid, 100, None)
        self.movement_repository.create(first_point.uuid, self.account.uuid, self.category.uuid, -20, None)
        self.movement_repository.create(second_point.uuid, self.account.uuid, self.category.uuid, 30, None)

        points = self.repository.list_points(self.account.uuid, 100, 3, 10)

        self.assertEqual(points, [80, 110, 110])

    def test_shopping_list_movements_affect_account_balance(self) -> None:
        shopping_list = self.create_event("Groceries", "SHOPPING_LIST", 10)
        self.movement_repository.create(shopping_list.uuid, self.account.uuid, self.category.uuid, -30, None)

        self.assertEqual(self.repository.get_balance_at(self.account.uuid, 10), -30)

    def test_balance_and_points_multiply_unit_value_by_quantity(self) -> None:
        event = self.create_event("Multiple items", occurred_at=100)
        self.movement_repository.create(event.uuid, self.account.uuid, self.category.uuid, -25, None, 4)

        self.assertEqual(self.repository.get_balance_at(self.account.uuid, 100), -100)
        self.assertEqual(self.repository.list_points(self.account.uuid, 100, 1, 10), [-100])

    def test_list_points_requires_positive_count_and_interval(self) -> None:
        """The caller explicitly controls both the number and width of points."""
        for point_count, point_interval in ((0, 86400), (-1, 86400), (1, 0), (1, -1)):
            with self.subTest(point_count=point_count, point_interval=point_interval):
                with self.assertRaises(ValueError):
                    self.repository.list_points(self.account.uuid, 100, point_count, point_interval)
