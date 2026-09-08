"""Integration tests for the ledger SQLite budget repository."""

from app.infrastructure.persistence.sqlite.ledger.repository.budget import SqliteBudgetRepository
from tests.integration.ledger_repository_test_case import LedgerRepositoryTestCase


class SqliteBudgetRepositoryTest(LedgerRepositoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repository = SqliteBudgetRepository(self.connection)
        self.currency = self.create_currency()
        self.account = self.create_account(currency=self.currency)
        self.category = self.create_category()

    def test_create_and_get_preserve_all_budget_fields(self) -> None:
        budget = self.create_budget(account=self.account, category=self.category)

        self.assertEqual(self.repository.get(budget.uuid), budget)
        self.assertEqual(budget.account_uuid, self.account.uuid)
        self.assertEqual(budget.category_uuid, self.category.uuid)
        self.assertEqual(budget.from_timestamp, 10)
        self.assertEqual(budget.to_timestamp, 20)
        self.assertEqual(budget.amount, 100)

    def test_get_by_name_returns_budget_and_unknown_name_returns_none(self) -> None:
        budget = self.create_budget(account=self.account, category=self.category)
        self.assertEqual(self.repository.get_by_name(budget.name), budget)
        self.assertIsNone(self.repository.get_by_name("Unknown"))

    def test_count_tracks_persisted_budgets(self) -> None:
        self.assertEqual(self.repository.count(), 0)
        self.create_budget("First", self.account, self.category)
        self.create_budget("Second", self.account, self.category)
        self.assertEqual(self.repository.count(), 2)

    def test_update_preserves_account_and_changes_mutable_fields(self) -> None:
        budget = self.create_budget(account=self.account, category=self.category)
        other_category = self.create_category("Leisure")
        updated = budget.model_copy(update={
            "category_uuid": other_category.uuid,
            "from_timestamp": 20,
            "to_timestamp": 40,
            "name": "Updated",
            "description": "Changed",
            "amount": 250,
        })

        self.repository.update(updated)

        stored = self.repository.get(budget.uuid)
        self.assertEqual(stored, updated)
        self.assertEqual(stored.account_uuid, self.account.uuid)

    def test_delete_removes_budget(self) -> None:
        budget = self.create_budget(account=self.account, category=self.category)
        self.repository.delete(budget.uuid)
        self.assertIsNone(self.repository.get(budget.uuid))
