"""Integration tests for cash-flow SQLite queries."""

from app.domain.ledger.model.account import Account
from app.domain.ledger.model.financial_event import FinancialEvent, FinancialEventType
from app.domain.ledger.model.financial_event_filter import FinancialEventFilter
from app.infrastructure.persistence.sqlite.ledger.repository.financial_movement import SqliteFinancialMovementRepository
from app.infrastructure.persistence.sqlite.ledger.repository.financial_event import SqliteFinancialEventRepository
from app.infrastructure.persistence.sqlite.ledger.repository.cash_flow_query import SqliteCashFlowQueryRepository
from tests.integration.ledger_repository_test_case import LedgerRepositoryTestCase


class SqliteCashFlowQueryRepositoryTest(LedgerRepositoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repository = SqliteCashFlowQueryRepository(self.connection)
        self.event_repository = SqliteFinancialEventRepository(self.connection)
        self.movement_repository = SqliteFinancialMovementRepository(self.connection)
        self.currency = self.create_currency()
        self.other_currency = self.create_currency("Dolár")
        self.account = self.create_account(currency=self.currency)
        self.other_account = self.create_account("Other real account", self.currency)
        self.foreign_currency_account = self.create_account("Dolár account", self.other_currency)
        self.category = self.create_category()

    def add_movement(self, description: str, occurred_at: int, value: int, account: Account | None = None, event_type: FinancialEventType = "TRANSACTION") -> FinancialEvent:
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
            FinancialEventFilter(from_timestamp=50, to_timestamp=300),
        )

        self.assertEqual(summary.currency_uuid, self.currency.uuid)
        self.assertEqual(summary.income, 100)
        self.assertEqual(summary.expense, 50)
        self.assertEqual(summary.event_count, 2)
        self.assertEqual(summary.income_movement_count, 1)
        self.assertEqual(summary.expense_movement_count, 2)

    def test_get_summary_applies_required_interval(self) -> None:
        """Only events inside the required half-open interval are represented."""
        self.add_movement("First", 100, 50)
        self.add_movement("Last", 200, -20)
        self.add_movement("Outside", 300, 1000)

        summary = self.repository.get_summary(
            self.currency.uuid,
            FinancialEventFilter(from_timestamp=100, to_timestamp=300),
        )

        self.assertEqual(summary.income, 50)
        self.assertEqual(summary.expense, 20)

    def test_get_summary_returns_zero_for_empty_interval(self) -> None:
        """An interval without matching movements returns a zero-valued summary."""
        summary = self.repository.get_summary(
            self.currency.uuid,
            FinancialEventFilter(from_timestamp=10, to_timestamp=20),
        )

        self.assertEqual(summary.income, 0)
        self.assertEqual(summary.expense, 0)
        self.assertEqual(summary.event_count, 0)

    def test_get_summary_aggregates_only_movements_matching_account_and_category(self) -> None:
        """Event matches do not include amounts from unrelated movements."""
        selected_account = self.account
        selected_category = self.create_category("Selected category")
        other_category = self.create_category("Other category")
        expected = self.create_event("Expected", occurred_at=100)
        excluded = self.create_event("Excluded", occurred_at=100)
        self.movement_repository.create(expected.uuid, selected_account.uuid, selected_category.uuid, 100, None)
        self.movement_repository.create(expected.uuid, self.other_account.uuid, selected_category.uuid, -40, None)
        self.movement_repository.create(expected.uuid, selected_account.uuid, other_category.uuid, -20, None)
        self.movement_repository.create(excluded.uuid, self.other_account.uuid, selected_category.uuid, -500, None)

        summary = self.repository.get_summary(
            self.currency.uuid,
            FinancialEventFilter(
                from_timestamp=0,
                to_timestamp=200,
                account_uuid=selected_account.uuid,
                category_uuid=selected_category.uuid,
            ),
        )

        self.assertEqual(summary.income, 100)
        self.assertEqual(summary.expense, 0)
        self.assertEqual(summary.event_count, 1)

    def test_event_matching_account_and_category_separately_contributes_zero(self) -> None:
        selected_category = self.create_category("Selected category")
        other_category = self.create_category("Other category")
        event = self.create_event("No common movement", occurred_at=100)
        self.movement_repository.create(event.uuid, self.account.uuid, other_category.uuid, -20, None)
        self.movement_repository.create(event.uuid, self.other_account.uuid, selected_category.uuid, -40, None)

        summary = self.repository.get_summary(
            self.currency.uuid,
            FinancialEventFilter(
                from_timestamp=0,
                to_timestamp=200,
                account_uuid=self.account.uuid,
                category_uuid=selected_category.uuid,
            ),
        )

        self.assertEqual(summary.income, 0)
        self.assertEqual(summary.expense, 0)
        self.assertEqual(summary.event_count, 0)
        self.assertEqual(summary.income_movement_count, 0)
        self.assertEqual(summary.expense_movement_count, 0)

    def test_shopping_list_movements_are_cash_flow(self) -> None:
        self.add_movement("Groceries", 100, -40, event_type="SHOPPING_LIST")

        summary = self.repository.get_summary(
            self.currency.uuid,
            FinancialEventFilter(from_timestamp=0, to_timestamp=200),
        )

        self.assertEqual(summary.expense, 40)
        self.assertEqual(summary.event_count, 1)

    def test_positive_reimbursement_is_income(self) -> None:
        self.add_movement("Reimbursement", 100, 40)

        summary = self.repository.get_summary(
            self.currency.uuid,
            FinancialEventFilter(from_timestamp=0, to_timestamp=200),
        )

        self.assertEqual(summary.income, 40)
        self.assertEqual(summary.expense, 0)
        self.assertEqual(summary.income_movement_count, 1)

    def test_summary_and_points_filter_by_event_description(self) -> None:
        self.add_movement("Salary", 100, 100)
        self.add_movement("Café dinner", 200, -20)
        filters = FinancialEventFilter(from_timestamp=0, to_timestamp=300, description_search="CAFE")

        summary = self.repository.get_summary(self.currency.uuid, filters)
        points = self.repository.list_points(self.currency.uuid, filters, 150)

        self.assertEqual((summary.income, summary.expense, summary.event_count), (0, 20, 1))
        self.assertEqual([(point.income, point.expense) for point in points], [(0, 0), (0, 20)])

    def test_summary_and_points_multiply_unit_values_without_multiplying_movement_counts(self) -> None:
        income = self.create_event("Multiple income", occurred_at=100)
        expense = self.create_event("Multiple expense", occurred_at=110)
        self.movement_repository.create(income.uuid, self.account.uuid, self.category.uuid, 20, None, 3)
        self.movement_repository.create(expense.uuid, self.account.uuid, self.category.uuid, -10, None, 4)
        filters = FinancialEventFilter(from_timestamp=100, to_timestamp=200)

        summary = self.repository.get_summary(self.currency.uuid, filters)
        points = self.repository.list_points(self.currency.uuid, filters, 100)

        self.assertEqual((summary.income, summary.expense), (60, 40))
        self.assertEqual((summary.income_movement_count, summary.expense_movement_count), (1, 1))
        self.assertEqual((points[0].income, points[0].expense), (60, 40))
        self.assertEqual((points[0].income_movement_count, points[0].expense_movement_count), (1, 1))

    def test_category_filter_aggregates_descendant_categories(self) -> None:
        parent = self.create_category("Parent")
        child = self.create_category("Child", parent)
        event = self.create_event("Child expense", occurred_at=100)
        self.movement_repository.create(event.uuid, self.account.uuid, child.uuid, -40, None)

        summary = self.repository.get_summary(
            self.currency.uuid,
            FinancialEventFilter(from_timestamp=0, to_timestamp=200, category_uuid=parent.uuid),
        )

        self.assertEqual(summary.expense, 40)
        self.assertEqual(summary.event_count, 1)

    def test_list_category_totals_groups_account_movements_by_category_and_excludes_transfers(self) -> None:
        groceries = self.create_category("Groceries")
        salary = self.create_category("Salary")
        income = self.create_event("Salary", occurred_at=100)
        expense = self.create_event("Groceries", occurred_at=120)
        transfer = self.create_event("Transfer", type="ACCOUNT_TRANSFER", occurred_at=140)
        other_account_event = self.create_event("Other account", occurred_at=150)
        self.movement_repository.create(income.uuid, self.account.uuid, salary.uuid, 100, None, 2)
        self.movement_repository.create(expense.uuid, self.account.uuid, groceries.uuid, -25, None, 3)
        self.movement_repository.create(transfer.uuid, self.account.uuid, groceries.uuid, -500, None)
        self.movement_repository.create(other_account_event.uuid, self.other_account.uuid, groceries.uuid, -700, None)

        totals = self.repository.list_category_totals(
            self.account.uuid,
            FinancialEventFilter(from_timestamp=100, to_timestamp=200, account_uuid=self.account.uuid),
        )

        by_category = {total.category_uuid: (total.income, total.expense) for total in totals}
        self.assertEqual(by_category[salary.uuid], (200, 0))
        self.assertEqual(by_category[groceries.uuid], (0, 75))
        self.assertEqual(len(by_category), 2)

    def test_list_points_groups_flow_from_caller_day_boundary_and_orders_it(self) -> None:
        """Daily buckets are anchored to the supplied first local-day timestamp."""
        self.add_movement("Second day", 86400 + 100, -20)
        self.add_movement("First day income", 100, 50)
        self.add_movement("First day expense", 200, -10)

        points = self.repository.list_points(
            self.currency.uuid,
            FinancialEventFilter(from_timestamp=100, to_timestamp=172900),
            86400,
        )

        self.assertEqual(points[0].income, 50)
        self.assertEqual(points[0].expense, 10)
        self.assertEqual(points[0].event_count, 2)
        self.assertEqual(points[1].income, 0)
        self.assertEqual(points[1].expense, 20)

    def test_list_points_truncates_the_final_point_to_the_filter_interval(self) -> None:
        """A partial final interval is retained instead of rejected."""
        self.add_movement("First point", 100, 50)
        self.add_movement("Truncated point", 1000, -20)
        filters = FinancialEventFilter(from_timestamp=100, to_timestamp=1100)

        points = self.repository.list_points(self.currency.uuid, filters, 600)

        self.assertEqual([(point.income, point.expense) for point in points], [(50, 0), (0, 20)])

    def test_list_points_requires_a_positive_point_width(self) -> None:
        filters = FinancialEventFilter(from_timestamp=100, to_timestamp=200)

        for point_width in (0, -1):
            with self.subTest(point_width=point_width):
                with self.assertRaises(ValueError):
                    self.repository.list_points(self.currency.uuid, filters, point_width)


if __name__ == "__main__":
    import unittest

    unittest.main()
