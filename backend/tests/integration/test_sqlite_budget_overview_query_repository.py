from app.infrastructure.persistence.sqlite.ledger.repository.budget_overview_query import SqliteBudgetOverviewQueryRepository
from app.infrastructure.persistence.sqlite.ledger.repository.financial_movement import SqliteFinancialMovementRepository
from tests.integration.ledger_repository_test_case import LedgerRepositoryTestCase


class SqliteBudgetOverviewQueryRepositoryTest(LedgerRepositoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repository = SqliteBudgetOverviewQueryRepository(self.connection)
        self.currency = self.create_currency()
        self.account = self.create_account("Checking", self.currency)
        self.other_account = self.create_account("Savings", self.currency)
        self.category = self.create_category("Food")
        self.child = self.create_category("Groceries", self.category)
        self.movements = SqliteFinancialMovementRepository(self.connection)

    def add_movement(self, occurred_at: int, value: int, quantity: int = 1, *, account=None, category=None, event_type="TRANSACTION") -> None:
        event = self.create_event(f"Event {occurred_at} {value}", event_type, occurred_at)
        self.movements.create(event.uuid, (account or self.account).uuid, (category or self.category).uuid, value, None, quantity)

    def test_page_classifies_future_active_and_finished_and_only_evaluates_nonfuture(self) -> None:
        finished = self.create_budget("Finished", self.account, self.category, 1, 10, 100)
        active = self.create_budget("Active", self.account, self.category, 10, 30, 100)
        future = self.create_budget("Future", self.account, self.category, 30, 40, 100)
        self.add_movement(5, -20)
        self.add_movement(15, -30)
        self.add_movement(20, -5, quantity=2, category=self.child)

        items = self.repository.list_page(20, ("FUTURE", "ACTIVE", "FINISHED"), None, None, None, 10, None, None)
        by_uuid = {item.budget.uuid: item for item in items}

        self.assertEqual(by_uuid[finished.uuid].state, "FINISHED")
        self.assertEqual(by_uuid[finished.uuid].spent_amount, 20)
        self.assertTrue(by_uuid[finished.uuid].fulfilled)
        self.assertEqual(by_uuid[active.uuid].state, "ACTIVE")
        self.assertEqual(by_uuid[active.uuid].spent_amount, 40)
        self.assertIsNone(by_uuid[active.uuid].fulfilled)
        self.assertEqual(by_uuid[future.uuid].state, "FUTURE")
        self.assertIsNone(by_uuid[future.uuid].spent_amount)
        self.assertIsNone(by_uuid[future.uuid].fulfilled)

    def test_evaluation_uses_exact_account_descendants_quantity_and_excludes_transfers(self) -> None:
        budget = self.create_budget("Monthly", self.account, self.category, 10, 30, 100)
        self.add_movement(15, -10, quantity=3, category=self.child)
        self.add_movement(15, -90, account=self.other_account)
        self.add_movement(15, -70, event_type="ACCOUNT_TRANSFER")
        self.add_movement(9, -50)

        item = self.repository.list_page(20, ("ACTIVE",), self.account.uuid, None, None, 10, None, None)[0]

        self.assertEqual(item.budget.uuid, budget.uuid)
        self.assertEqual(item.spent_amount, 30)

    def test_finished_budget_uses_exclusive_end_and_active_budget_includes_current_second(self) -> None:
        finished = self.create_budget("Finished", self.account, self.category, 10, 20, 100)
        active = self.create_budget("Active", self.account, self.category, 10, 30, 100)
        self.add_movement(20, -25)

        items = self.repository.list_page(20, ("ACTIVE", "FINISHED"), None, None, None, 10, None, None)
        by_uuid = {item.budget.uuid: item for item in items}

        self.assertEqual(by_uuid[finished.uuid].spent_amount, 0)
        self.assertEqual(by_uuid[active.uuid].spent_amount, 25)

    def test_page_filters_state_account_name_and_cursor_before_evaluation(self) -> None:
        alpha = self.create_budget("Alpha", self.account, self.category, 10, 30, 100)
        bravo = self.create_budget("Bravo", self.account, self.category, 10, 30, 100)
        self.create_budget("Future", self.account, self.category, 40, 50, 100)
        self.create_budget("Other account", self.other_account, self.category, 10, 30, 100)

        first = self.repository.list_page(20, ("ACTIVE",), self.account.uuid, None, "a", 1, None, None)
        second = self.repository.list_page(20, ("ACTIVE",), self.account.uuid, None, None, 10, first[0].budget.name, first[0].budget.uuid)

        self.assertEqual([item.budget.uuid for item in first], [alpha.uuid])
        self.assertEqual([item.budget.uuid for item in second], [bravo.uuid])


    def test_page_category_filter_includes_descendant_budget_categories(self) -> None:
        root_budget = self.create_budget("Root", self.account, self.category, 10, 30, 100)
        child_budget = self.create_budget("Child", self.account, self.child, 10, 30, 100)
        other = self.create_category("Other")
        self.create_budget("Other", self.account, other, 10, 30, 100)

        items = self.repository.list_page(20, ("ACTIVE",), None, self.category.uuid, None, 10, None, None)

        self.assertEqual({item.budget.uuid for item in items}, {root_budget.uuid, child_budget.uuid})

    def test_currency_listing_orders_over_budget_then_highest_usage_then_earliest_end(self) -> None:
        over = self.create_budget("Over", self.account, self.category, 10, 50, 100)
        near = self.create_budget("Near", self.account, self.category, 10, 40, 100)
        lower = self.create_budget("Lower", self.account, self.category, 10, 35, 200)
        self.create_budget("Future", self.account, self.category, 30, 40, 100)
        self.add_movement(15, -120)
        # The same spending applies to all three active budgets: 120%, 120%, 60%.
        # Give Near a smaller category scope so it can be ranked below Over despite the same account.
        other_category = self.create_category("Other")
        near_changed = near.model_copy(update={"category_uuid": other_category.uuid})
        from app.infrastructure.persistence.sqlite.ledger.repository.budget import SqliteBudgetRepository
        SqliteBudgetRepository(self.connection).update(near_changed)
        event = self.create_event("Near spend", "TRANSACTION", 15)
        self.movements.create(event.uuid, self.account.uuid, other_category.uuid, -95, None, 1)

        other_currency = self.create_currency("Other currency")
        foreign_account = self.create_account("Foreign", other_currency)
        self.create_budget("Foreign budget", foreign_account, self.category, 10, 50, 1)
        self.add_movement(15, -500, account=foreign_account)

        items = self.repository.list_for_currency(20, self.currency.uuid, 3)

        self.assertEqual([item.budget.uuid for item in items], [over.uuid, near.uuid, lower.uuid])
        self.assertEqual([item.spent_amount for item in items], [120, 95, 120])
