"""Integration tests for the ledger SQLite account repository."""

import sqlite3
from uuid import uuid4

from pydantic import ValidationError

from app.infrastructure.persistence.sqlite.ledger.repository.account import SqliteAccountRepository
from tests.integration.ledger_repository_test_case import LedgerRepositoryTestCase


class SqliteAccountRepositoryTest(LedgerRepositoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repository = SqliteAccountRepository(self.connection)
        self.currency = self.create_currency()

    def test_create_and_get_preserve_account_fields(self) -> None:
        """create generates identity and stores the supplied currency relation."""
        account = self.repository.create("Checking", "Daily account", self.currency.uuid)

        self.assertEqual(self.repository.get(account.uuid), account)
        self.assertEqual(account.note, "Daily account")
        self.assertEqual(account.currency_uuid, self.currency.uuid)

    def test_create_requires_an_existing_currency(self) -> None:
        """The database foreign key rejects an unknown currency."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.create("Checking", None, uuid4())

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
            self.repository.update_name(account.uuid, "x" * 31)
        with self.assertRaises(ValidationError):
            self.repository.update_note(account.uuid, "x" * 301)

    def test_list_page_orders_and_rejects_identity_sorting(self) -> None:
        """Neither entity nor currency UUID is exposed as a sort option."""
        for name in ("Charlie", "Alpha", "Bravo"):
            self.repository.create(name, None, self.currency.uuid)

        page = self.repository.list_page(2, 1, "name", True)

        self.assertEqual([account.name for account in page], ["Bravo"])
        for sort_key in ("uuid", "currency_uuid"):
            with self.subTest(sort_key=sort_key):
                with self.assertRaises(ValueError):
                    self.repository.list_page(1, 10, sort_key, True)

    def test_repository_does_not_commit_its_changes(self) -> None:
        """Rolling back removes the account but preserves committed prerequisites."""
        self.connection.commit()
        self.repository.create("Checking", None, self.currency.uuid)

        self.connection.rollback()

        self.assertEqual(self.repository.list_all(), [])


if __name__ == "__main__":
    import unittest

    unittest.main()
