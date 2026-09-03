"""Integration tests for the ledger SQLite budget repository."""

import sqlite3
from uuid import uuid4

from pydantic import ValidationError

from app.infrastructure.persistence.sqlite.ledger.repository.budget import SqliteBudgetRepository
from tests.integration.ledger_repository_test_case import LedgerRepositoryTestCase


class SqliteBudgetRepositoryTest(LedgerRepositoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repository = SqliteBudgetRepository(self.connection)
        self.currency = self.create_currency()
        self.category = self.create_category()

    def test_create_and_get_preserve_all_budget_fields(self) -> None:
        """create generates identity and stores the supplied budget configuration."""
        budget = self.create_budget(currency=self.currency, category=self.category)

        self.assertEqual(self.repository.get(budget.uuid), budget)
        self.assertEqual(budget.from_timestamp, 10)
        self.assertEqual(budget.to_timestamp, 20)
        self.assertEqual(budget.amount, 100)
        self.assertEqual(budget.icon, "ReceiptText")
        self.assertEqual(budget.color_code, b"\x80\x80\x80")

    def test_create_requires_existing_category_and_currency(self) -> None:
        """Foreign keys reject unknown category or currency identities."""
        for category_uuid, currency_uuid in ((uuid4(), self.currency.uuid), (self.category.uuid, uuid4())):
            with self.subTest(category_uuid=category_uuid, currency_uuid=currency_uuid):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.repository.create(category_uuid, currency_uuid, 10, 20, "Monthly", "Spending", 100, "ReceiptText", b"\x80\x80\x80")

    def test_updates_mutable_budget_fields_without_changing_currency(self) -> None:
        """Budget updates preserve identity and immutable currency relation."""
        budget = self.create_budget(currency=self.currency, category=self.category)
        other_category = self.create_category("Leisure")

        self.repository.update_period(budget.uuid, 20, 30)
        self.repository.update_name(budget.uuid, "Updated")
        self.repository.update_description(budget.uuid, "Updated spending")
        self.repository.update_amount(budget.uuid, 200)
        self.repository.update_category(budget.uuid, other_category.uuid)

        updated = self.repository.get(budget.uuid)
        assert updated is not None
        self.assertEqual(updated.from_timestamp, 20)
        self.assertEqual(updated.to_timestamp, 30)
        self.assertEqual(updated.name, "Updated")
        self.assertEqual(updated.description, "Updated spending")
        self.assertEqual(updated.amount, 200)
        self.assertEqual(updated.category_uuid, other_category.uuid)
        self.assertEqual(updated.currency_uuid, self.currency.uuid)

    def test_updates_validate_budget_constraints(self) -> None:
        """Update methods enforce period, text and amount constraints."""
        budget = self.create_budget(currency=self.currency, category=self.category)

        with self.assertRaises(ValidationError):
            self.repository.update_period(budget.uuid, 20, 10)
        with self.assertRaises(ValidationError):
            self.repository.update_name(budget.uuid, "x" * 51)
        with self.assertRaises(ValidationError):
            self.repository.update_description(budget.uuid, "")
        with self.assertRaises(ValidationError):
            self.repository.update_amount(budget.uuid, -1)

    def test_updates_icon_and_color_without_changing_budget_scope(self) -> None:
        """Appearance changes preserve the budget period and relations."""
        budget = self.create_budget(currency=self.currency, category=self.category)

        self.repository.update_icon(budget.uuid, "💰")
        self.repository.update_color_code(budget.uuid, b"\xff\x80\x00")

        updated = self.repository.get(budget.uuid)
        assert updated is not None
        self.assertEqual(updated.icon, "💰")
        self.assertEqual(updated.color_code, b"\xff\x80\x00")
        self.assertEqual(updated.category_uuid, budget.category_uuid)

    def test_add_list_and_remove_accounts(self) -> None:
        """Budget-account relations support the complete basic lifecycle."""
        budget = self.create_budget(currency=self.currency, category=self.category)
        first = self.create_account("Checking", self.currency)
        second = self.create_account("Savings", self.currency)

        self.repository.add_account(budget.uuid, first.uuid)
        self.repository.add_account(budget.uuid, second.uuid)

        self.assertCountEqual(self.repository.list_accounts(budget.uuid), [first, second])

        self.repository.remove_account(budget.uuid, first.uuid)
        self.assertEqual(self.repository.list_accounts(budget.uuid), [second])

    def test_add_account_rejects_a_different_currency(self) -> None:
        """The composite foreign key keeps all budget accounts in one currency."""
        budget = self.create_budget(currency=self.currency, category=self.category)
        other_currency = self.create_currency("Dollar")
        account = self.create_account("Dollar account", other_currency)

        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.add_account(budget.uuid, account.uuid)

    def test_list_page_orders_and_rejects_all_uuid_sorting(self) -> None:
        """Budget pagination exposes domain values but no relation UUID."""
        for name in ("Charlie", "Alpha", "Bravo"):
            self.create_budget(name, self.currency, self.category)

        page = self.repository.list_page(1, 2, "name", True)
        all_budgets = self.repository.list_page(1, 200, "name", False)

        self.assertEqual([budget.name for budget in page], ["Alpha", "Bravo"])
        self.assertEqual([budget.name for budget in all_budgets], ["Charlie", "Bravo", "Alpha"])
        for sort_key in ("uuid", "category_uuid", "currency_uuid"):
            with self.subTest(sort_key=sort_key):
                with self.assertRaises(ValueError):
                    self.repository.list_page(1, 200, sort_key, True)

    def test_repository_does_not_commit_its_changes(self) -> None:
        """Rolling back removes the budget but preserves committed prerequisites."""
        self.connection.commit()
        self.create_budget(currency=self.currency, category=self.category)

        self.connection.rollback()

        self.assertEqual(self.repository.list_page(1, 200, "name", True), [])


if __name__ == "__main__":
    import unittest

    unittest.main()
