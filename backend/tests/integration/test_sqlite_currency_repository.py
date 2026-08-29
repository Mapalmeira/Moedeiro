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
        currency = self.repository.create("Real", "R$", None, 2)

        self.assertEqual(self.repository.get(currency.uuid), currency)
        self.assertEqual(currency.name, "Real")
        self.assertEqual(currency.prefix, "R$")
        self.assertIsNone(currency.suffix)
        self.assertEqual(currency.decimal_places, 2)

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

    def test_list_page_orders_and_rejects_uuid_sorting(self) -> None:
        """Pagination accepts model fields but never UUID as a public sort key."""
        self.repository.create("Charlie", None, None, 2)
        self.repository.create("Alpha", None, None, 2)
        self.repository.create("Bravo", None, None, 2)

        page = self.repository.list_page(1, 2, "name", True)

        self.assertEqual([currency.name for currency in page], ["Alpha", "Bravo"])
        with self.assertRaises(ValueError):
            self.repository.list_page(1, 10, "uuid", True)

    def test_repository_does_not_commit_its_changes(self) -> None:
        """Transaction ownership remains with the unit of work."""
        self.repository.create("Real", "R$", None, 2)

        self.connection.rollback()

        self.assertEqual(self.repository.list_all(), [])


if __name__ == "__main__":
    import unittest

    unittest.main()
