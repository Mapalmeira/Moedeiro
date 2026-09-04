"""Integration tests for budget-status SQLite queries."""

from app.domain.ledger.model.account import Account
from app.domain.ledger.model.category import Category
from app.domain.ledger.model.financial_event import FinancialEventType
from app.infrastructure.persistence.sqlite.ledger.repository.budget import SqliteBudgetRepository
from app.infrastructure.persistence.sqlite.ledger.repository.budget_status_query import SqliteBudgetStatusQueryRepository
from app.infrastructure.persistence.sqlite.ledger.repository.financial_movement import SqliteFinancialMovementRepository
from tests.integration.ledger_repository_test_case import LedgerRepositoryTestCase


class SqliteBudgetStatusQueryRepositoryTest(LedgerRepositoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repository = SqliteBudgetStatusQueryRepository(self.connection)
        self.budget_repository = SqliteBudgetRepository(self.connection)
        self.movement_repository = SqliteFinancialMovementRepository(self.connection)
        self.currency = self.create_currency()
        self.category = self.create_category()
        self.other_category = self.create_category("Other category")
        self.account = self.create_account(currency=self.currency)
        self.other_account = self.create_account("Other account", self.currency)
        self.budget = self.create_budget(currency=self.currency, category=self.category)
        self.budget_repository.add_account(self.budget.uuid, self.account.uuid)

    def add_movement(self, description: str, occurred_at: int, value: int, account: Account | None = None, category: Category | None = None, event_type: FinancialEventType = "TRANSACTION") -> None:
        event = self.create_event(description, event_type, occurred_at)
        self.movement_repository.create(
            event.uuid,
            (account or self.account).uuid,
            (category or self.category).uuid,
            value,
            None,
        )

    def test_get_status_sums_expenses_from_budget_start_through_timestamp(self) -> None:
        """Only negative matching movements from configured accounts are expenses."""
        self.add_movement("Before budget", 9, -500)
        self.add_movement("At start", 10, -60)
        self.add_movement("At timestamp", 15, -50)
        self.add_movement("After timestamp", 16, -500)
        self.add_movement("Reimbursement", 12, 300)
        transfer = self.create_event("Transfer", "ACCOUNT_TRANSFER", 13)
        self.movement_repository.create(transfer.uuid, self.account.uuid, self.category.uuid, -400, None)
        self.movement_repository.create(transfer.uuid, self.other_account.uuid, self.category.uuid, 400, None)
        self.add_movement("Other category", 14, -600, category=self.other_category)
        self.add_movement("Other account", 14, -700, account=self.other_account)

        status = self.repository.get_status(self.budget.uuid, 15)

        assert status is not None
        self.assertEqual(status.budgeted_amount, 100)
        self.assertEqual(status.spent_amount, 110)
        self.assertTrue(status.over_budget)

    def test_exact_budget_amount_is_not_over_budget(self) -> None:
        """over_budget becomes true only after spending exceeds the configured amount."""
        self.add_movement("Expense", 10, -100)

        status = self.repository.get_status(self.budget.uuid, 15)

        assert status is not None
        self.assertEqual(status.spent_amount, 100)
        self.assertFalse(status.over_budget)

    def test_positive_reimbursement_does_not_reduce_spending(self) -> None:
        self.add_movement("Expense", 10, -100)
        self.add_movement("Reimbursement", 11, 40)

        status = self.repository.get_status(self.budget.uuid, 15)

        assert status is not None
        self.assertEqual(status.spent_amount, 100)

    def test_shopping_list_expenses_are_included(self) -> None:
        self.add_movement("Groceries", 10, -40, event_type="SHOPPING_LIST")

        status = self.repository.get_status(self.budget.uuid, 15)

        assert status is not None
        self.assertEqual(status.spent_amount, 40)

    def test_spent_amount_multiplies_unit_value_by_quantity(self) -> None:
        event = self.create_event("Multiple items", occurred_at=10)
        self.movement_repository.create(event.uuid, self.account.uuid, self.category.uuid, -25, None, 3)

        status = self.repository.get_status(self.budget.uuid, 15)

        assert status is not None
        self.assertEqual(status.spent_amount, 75)

    def test_get_status_returns_none_outside_budget_interval(self) -> None:
        """A budget is active on its inclusive lower and exclusive upper boundary."""
        self.assertIsNone(self.repository.get_status(self.budget.uuid, 9))
        self.assertIsNotNone(self.repository.get_status(self.budget.uuid, 10))
        self.assertIsNone(self.repository.get_status(self.budget.uuid, 20))

    def test_list_page_returns_only_budgets_active_at_timestamp(self) -> None:
        """The collection excludes budgets whose periods do not contain the timestamp."""
        active = self.budget
        inactive = self.create_budget("Later", self.currency, self.category)
        self.budget_repository.update(inactive.model_copy(update={"from_timestamp": 20, "to_timestamp": 30}))

        statuses = self.repository.list_page(15, 1, 200)

        self.assertEqual([status.budget_uuid for status in statuses], [active.uuid])

    def test_list_page_aggregates_overlapping_budgets_independently(self) -> None:
        other_budget = self.create_budget("Other account budget", self.currency, self.category)
        self.budget_repository.add_account(other_budget.uuid, self.other_account.uuid)
        self.add_movement("First account", 10, -30, account=self.account)
        self.add_movement("Other account", 10, -40, account=self.other_account)

        statuses = {status.budget_uuid: status for status in self.repository.list_page(15, 1, 200)}

        self.assertEqual(statuses[self.budget.uuid].spent_amount, 30)
        self.assertEqual(statuses[other_budget.uuid].spent_amount, 40)

    def test_list_page_orders_by_budget_name_and_applies_pagination(self) -> None:
        alpha = self.create_budget("Alpha", self.currency, self.category)
        bravo = self.create_budget("Bravo", self.currency, self.category)

        first_page = self.repository.list_page(15, 1, 2)
        second_page = self.repository.list_page(15, 2, 2)

        self.assertEqual([status.budget_uuid for status in first_page], [alpha.uuid, bravo.uuid])
        self.assertEqual([status.budget_uuid for status in second_page], [self.budget.uuid])

    def test_budget_without_accounts_includes_every_account_in_its_currency(self) -> None:
        """Absent account selectors make the budget apply to its complete currency."""
        empty_budget = self.create_budget("Empty", self.currency, self.category)
        other_currency = self.create_currency("Dollar")
        other_currency_account = self.create_account("Dollar account", other_currency)
        self.add_movement("First expense", 10, -50, account=self.account)
        self.add_movement("Second expense", 11, -30, account=self.other_account)
        self.add_movement("Other currency", 12, -500, account=other_currency_account)

        status = self.repository.get_status(empty_budget.uuid, 15)

        assert status is not None
        self.assertEqual(status.spent_amount, 80)

    def test_budget_includes_expenses_from_descendant_categories(self) -> None:
        child = self.create_category("Child", self.category)
        grandchild = self.create_category("Grandchild", child)
        self.add_movement("Descendant expense", 10, -40, category=grandchild)

        status = self.repository.get_status(self.budget.uuid, 15)

        assert status is not None
        self.assertEqual(status.spent_amount, 40)


if __name__ == "__main__":
    import unittest

    unittest.main()
