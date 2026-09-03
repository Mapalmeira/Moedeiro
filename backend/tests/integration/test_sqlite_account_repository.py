"""Integration tests for the ledger SQLite account repository."""

import sqlite3
from uuid import uuid4

from pydantic import ValidationError

from app.infrastructure.persistence.sqlite.ledger.repository.account import SqliteAccountRepository
from app.infrastructure.persistence.sqlite.ledger.repository.budget import SqliteBudgetRepository
from app.infrastructure.persistence.sqlite.ledger.repository.financial_movement import SqliteFinancialMovementRepository
from tests.integration.ledger_repository_test_case import LedgerRepositoryTestCase


class SqliteAccountRepositoryTest(LedgerRepositoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repository = SqliteAccountRepository(self.connection)
        self.currency = self.create_currency()

    def test_create_and_get_preserve_account_fields(self) -> None:
        """create generates identity and stores the supplied currency relation."""
        account = self.repository.create("Checking", "Daily account", self.currency.uuid, "WalletCards", b"\x80\x80\x80")

        self.assertEqual(self.repository.get(account.uuid), account)
        self.assertEqual(account.note, "Daily account")
        self.assertEqual(account.currency_uuid, self.currency.uuid)
        self.assertEqual(account.icon, "WalletCards")
        self.assertEqual(account.color_code, b"\x80\x80\x80")
        self.assertEqual(self.repository.get_by_name("Checking"), account)

    def test_create_requires_an_existing_currency(self) -> None:
        """The database foreign key rejects an unknown currency."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.create("Checking", None, uuid4(), "WalletCards", b"\x80\x80\x80")

    def test_updates_name_and_optional_note_without_changing_currency(self) -> None:
        """The account currency remains immutable through repository updates."""
        account = self.create_account(currency=self.currency)

        self.repository.update_name(account.uuid, "Savings")
        self.repository.update_note(account.uuid, "Reserve")
        self.repository.update_note(account.uuid, None)

        updated = self.repository.get(account.uuid)
        assert updated is not None
        self.assertEqual(updated.name, "Savings")
        self.assertIsNone(updated.note)
        self.assertEqual(updated.currency_uuid, self.currency.uuid)

    def test_updates_validate_text_limits(self) -> None:
        """Updates enforce Account name and note constraints before SQL execution."""
        account = self.create_account(currency=self.currency)

        with self.assertRaises(ValidationError):
            self.repository.update_name(account.uuid, "x" * 51)
        with self.assertRaises(ValidationError):
            self.repository.update_note(account.uuid, "x" * 301)

    def test_updates_icon_and_color_without_changing_account_relations(self) -> None:
        """Appearance changes preserve the account name and currency."""
        account = self.create_account(currency=self.currency)

        self.repository.update_icon(account.uuid, "💳")
        self.repository.update_color_code(account.uuid, b"\xff\x80\x00")

        updated = self.repository.get(account.uuid)
        assert updated is not None
        self.assertEqual(updated.icon, "💳")
        self.assertEqual(updated.color_code, b"\xff\x80\x00")
        self.assertEqual(updated.currency_uuid, account.currency_uuid)

    def test_list_page_orders_and_rejects_identity_sorting(self) -> None:
        """Neither entity nor currency UUID is exposed as a sort option."""
        for name in ("Charlie", "Alpha", "Bravo"):
            self.repository.create(name, None, self.currency.uuid, "WalletCards", b"\x80\x80\x80")

        page = self.repository.list_page(2, 1, "name", True)
        all_accounts = self.repository.list_page(1, 200, "name", False)

        self.assertEqual([account.name for account in page], ["Bravo"])
        self.assertEqual([account.name for account in all_accounts], ["Charlie", "Bravo", "Alpha"])
        for sort_key in ("uuid", "currency_uuid"):
            with self.subTest(sort_key=sort_key):
                with self.assertRaises(ValueError):
                    self.repository.list_page(1, 200, sort_key, True)

        with self.assertRaises(ValueError):
            self.repository.list_page(1, 201, "name", True)

    def test_is_in_use_detects_financial_movements_and_budgets(self) -> None:
        movement_account = self.create_account("Movement", self.currency)
        budget_account = self.create_account("Budget", self.currency)
        unused_account = self.create_account("Unused", self.currency)
        category = self.create_category()
        event = self.create_event()
        SqliteFinancialMovementRepository(self.connection).create(event.uuid, movement_account.uuid, category.uuid, -100, None)
        budget = self.create_budget(currency=self.currency, category=category)
        SqliteBudgetRepository(self.connection).add_account(budget.uuid, budget_account.uuid)

        self.assertTrue(self.repository.is_in_use(movement_account.uuid))
        self.assertTrue(self.repository.is_in_use(budget_account.uuid))
        self.assertFalse(self.repository.is_in_use(unused_account.uuid))

    def test_delete_removes_only_the_selected_account(self) -> None:
        deleted = self.create_account("Deleted", self.currency)
        preserved = self.create_account("Preserved", self.currency)

        self.repository.delete(deleted.uuid)

        self.assertIsNone(self.repository.get(deleted.uuid))
        self.assertEqual(self.repository.get(preserved.uuid), preserved)

    def test_repository_does_not_commit_its_changes(self) -> None:
        """Rolling back removes the account but preserves committed prerequisites."""
        self.connection.commit()
        self.repository.create("Checking", None, self.currency.uuid, "WalletCards", b"\x80\x80\x80")

        self.connection.rollback()

        self.assertEqual(self.repository.list_page(1, 200, "name", True), [])


if __name__ == "__main__":
    import unittest

    unittest.main()
