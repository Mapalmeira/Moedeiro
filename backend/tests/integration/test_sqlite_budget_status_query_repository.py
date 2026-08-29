"""Integration tests for budget-status SQLite queries."""

from app.domain.ledger.model.account import Account
from app.domain.ledger.model.category import Category
from app.domain.ledger.model.transaction_event import TransactionEventType
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

    def add_movement(self, description: str, occurred_at: int, value: int, account: Account | None = None, category: Category | None = None, event_type: TransactionEventType = "TRANSACTION") -> None:
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

    def test_get_status_returns_none_outside_budget_interval(self) -> None:
        """A budget is active on its inclusive lower and exclusive upper boundary."""
        self.assertIsNone(self.repository.get_status(self.budget.uuid, 9))
        self.assertIsNotNone(self.repository.get_status(self.budget.uuid, 10))
        self.assertIsNone(self.repository.get_status(self.budget.uuid, 20))

    def test_list_statuses_returns_only_budgets_active_at_timestamp(self) -> None:
        """The collection excludes budgets whose periods do not contain the timestamp."""
        active = self.budget
        inactive = self.create_budget("Later", self.currency, self.category)
        self.budget_repository.update_period(inactive.uuid, 20, 30)

        statuses = self.repository.list_statuses(15)

        self.assertEqual([status.budget_uuid for status in statuses], [active.uuid])

    def test_budget_without_accounts_has_zero_spending(self) -> None:
        """Movements only participate after their account is attached to the budget."""
        empty_budget = self.create_budget("Empty", self.currency, self.category)
        self.add_movement("Expense", 10, -50)

        status = self.repository.get_status(empty_budget.uuid, 15)

        assert status is not None
        self.assertEqual(status.spent_amount, 0)

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
