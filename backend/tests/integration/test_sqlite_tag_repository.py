"""Integration tests for the ledger SQLite tag repository."""

import sqlite3

from pydantic import ValidationError

from app.infrastructure.persistence.sqlite.ledger.repository.tag import SqliteTagRepository
from tests.integration.ledger_repository_test_case import LedgerRepositoryTestCase


class SqliteTagRepositoryTest(LedgerRepositoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repository = SqliteTagRepository(self.connection)

    def test_create_get_update_and_list_all(self) -> None:
        """Basic operations preserve identity while changing the tag name."""
        tag = self.repository.create("Old")

        self.repository.update_name(tag.uuid, "New")

        updated = self.repository.get(tag.uuid)
        assert updated is not None
        self.assertEqual(updated.name, "New")
        self.assertEqual(updated.uuid, tag.uuid)

    def test_create_and_update_validate_name_limit(self) -> None:
        """Create and update share the Tag model constraints."""
        with self.assertRaises(ValidationError):
            self.repository.create("x" * 31)

        tag = self.create_tag()
        with self.assertRaises(ValidationError):
            self.repository.update_name(tag.uuid, "x" * 31)

    def test_database_rejects_duplicate_names(self) -> None:
        """The schema keeps tag names unique."""
        self.repository.create("Important")

        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.create("Important")

    def test_list_page_orders_and_rejects_uuid_sorting(self) -> None:
        """Tag pagination only exposes name as a sorting field."""
        for name in ("Charlie", "Alpha", "Bravo"):
            self.repository.create(name)

        page = self.repository.list_page(1, 2, "name", True)

        self.assertEqual([tag.name for tag in page], ["Alpha", "Bravo"])
        with self.assertRaises(ValueError):
            self.repository.list_page(1, 10, "uuid", True)


if __name__ == "__main__":
    import unittest

    unittest.main()
