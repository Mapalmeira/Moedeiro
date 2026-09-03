"""Integration tests for the ledger SQLite currency repository."""

from pydantic import ValidationError

from app.infrastructure.persistence.sqlite.ledger.repository.currency import SqliteCurrencyRepository
from tests.integration.ledger_repository_test_case import LedgerRepositoryTestCase


class SqliteCurrencyRepositoryTest(LedgerRepositoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repository = SqliteCurrencyRepository(self.connection)

    def test_create_and_get_preserve_all_currency_fields(self) -> None:
        """create generates an identity and persists optional formatting fields."""
        currency = self.repository.create("Real", "R$", None, 2, "R$", b"\x80\x80\x80")

        self.assertEqual(self.repository.get(currency.uuid), currency)
        self.assertEqual(currency.name, "Real")
        self.assertEqual(currency.prefix, "R$")
        self.assertIsNone(currency.suffix)
        self.assertEqual(currency.decimal_places, 2)
        self.assertEqual(currency.icon, "R$")
        self.assertEqual(currency.color_code, b"\x80\x80\x80")

    def test_get_returns_none_for_unknown_currency(self) -> None:
        """An absent currency is represented by None."""
        from uuid import uuid4

        self.assertIsNone(self.repository.get(uuid4()))

    def test_updates_name_prefix_and_suffix_independently(self) -> None:
        """Each update changes only its selected mutable field."""
        currency = self.create_currency()

        self.repository.update_name(currency.uuid, "Brazilian Real")
        self.repository.update_prefix(currency.uuid, None)
        self.repository.update_suffix(currency.uuid, " BRL")

        updated = self.repository.get(currency.uuid)
        assert updated is not None
        self.assertEqual(updated.name, "Brazilian Real")
        self.assertIsNone(updated.prefix)
        self.assertEqual(updated.suffix, " BRL")
        self.assertEqual(updated.decimal_places, 2)

    def test_updates_validate_text_limits(self) -> None:
        """Update methods enforce the same limits as Currency."""
        currency = self.create_currency()

        for method, value in ((self.repository.update_name, "x" * 31), (self.repository.update_prefix, "x" * 11), (self.repository.update_suffix, "x" * 11)):
            with self.subTest(method=method.__name__):
                with self.assertRaises(ValidationError):
                    method(currency.uuid, value)

    def test_updates_icon_and_color_without_changing_formatting(self) -> None:
        """Currency appearance changes preserve formatting properties."""
        currency = self.create_currency()

        self.repository.update_icon(currency.uuid, "💵")
        self.repository.update_color_code(currency.uuid, b"\xff\x80\x00")

        updated = self.repository.get(currency.uuid)
        assert updated is not None
        self.assertEqual(updated.icon, "💵")
        self.assertEqual(updated.color_code, b"\xff\x80\x00")
        self.assertEqual(updated.decimal_places, currency.decimal_places)

    def test_list_page_orders_and_rejects_uuid_sorting(self) -> None:
        """Pagination accepts model fields but never UUID as a public sort key."""
        self.repository.create("Charlie", None, None, 2, "$", b"\x80\x80\x80")
        self.repository.create("Alpha", None, None, 2, "$", b"\x80\x80\x80")
        self.repository.create("Bravo", None, None, 2, "$", b"\x80\x80\x80")

        page = self.repository.list_page(1, 2, "name", True)
        all_currencies = self.repository.list_page(1, 200, "name", False)

        self.assertEqual([currency.name for currency in page], ["Alpha", "Bravo"])
        self.assertEqual([currency.name for currency in all_currencies], ["Charlie", "Bravo", "Alpha"])
        with self.assertRaises(ValueError):
            self.repository.list_page(1, 200, "uuid", True)
        with self.assertRaises(ValueError):
            self.repository.list_page(1, 201, "name", True)

    def test_is_in_use_detects_accounts_and_budgets(self) -> None:
        account_currency = self.create_currency("Account currency")
        budget_currency = self.create_currency("Budget currency")
        unused_currency = self.create_currency("Unused currency")
        category = self.create_category()
        self.create_account(currency=account_currency)
        self.create_budget(currency=budget_currency, category=category)

        self.assertTrue(self.repository.is_in_use(account_currency.uuid))
        self.assertTrue(self.repository.is_in_use(budget_currency.uuid))
        self.assertFalse(self.repository.is_in_use(unused_currency.uuid))

    def test_delete_removes_only_the_selected_currency(self) -> None:
        deleted = self.create_currency("Deleted")
        preserved = self.create_currency("Preserved")

        self.repository.delete(deleted.uuid)

        self.assertIsNone(self.repository.get(deleted.uuid))
        self.assertEqual(self.repository.get(preserved.uuid), preserved)

    def test_repository_does_not_commit_its_changes(self) -> None:
        """Transaction ownership remains with the unit of work."""
        self.repository.create("Real", "R$", None, 2, "R$", b"\x80\x80\x80")

        self.connection.rollback()

        self.assertEqual(self.repository.list_page(1, 200, "name", True), [])


if __name__ == "__main__":
    import unittest

    unittest.main()
