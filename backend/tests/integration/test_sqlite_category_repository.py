"""Integration tests for the ledger SQLite category repository."""

import sqlite3

from pydantic import ValidationError

from app.domain.ledger.model.category_tree_node import CategoryTreeNode
from app.infrastructure.persistence.sqlite.ledger.repository.category import SqliteCategoryRepository
from tests.integration.ledger_repository_test_case import LedgerRepositoryTestCase


class SqliteCategoryRepositoryTest(LedgerRepositoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repository = SqliteCategoryRepository(self.connection)

    def test_create_get_and_update_parent(self) -> None:
        """A category can acquire and clear an existing parent."""
        parent = self.create_category("Parent")
        child = self.repository.create("Child", "Circle", b"\x80\x80\x80", None)

        self.repository.update_parent(child.uuid, parent.uuid)
        updated = self.repository.get(child.uuid)
        assert updated is not None
        self.assertEqual(updated.parent_uuid, parent.uuid)

        self.repository.update_parent(child.uuid, None)
        cleared = self.repository.get(child.uuid)
        assert cleared is not None
        self.assertIsNone(cleared.parent_uuid)

    def test_update_icon_and_color_changes_only_appearance(self) -> None:
        """The category appearance persists independently from its hierarchy."""
        category = self.create_category()

        self.repository.update_icon(category.uuid, "Utensils")
        self.repository.update_color_code(category.uuid, b"\xff\x80\x00")

        updated = self.repository.get(category.uuid)
        assert updated is not None
        self.assertEqual(updated.icon, "Utensils")
        self.assertEqual(updated.color_code, b"\xff\x80\x00")
        self.assertEqual(updated.parent_uuid, category.parent_uuid)

    def test_update_name_validates_model_limit(self) -> None:
        """Category names are validated before an update is executed."""
        category = self.create_category()

        with self.assertRaises(ValidationError):
            self.repository.update_name(category.uuid, "x" * 31)

    def test_deleting_parent_cascades_to_children(self) -> None:
        """The schema relation applies its configured parent cascade."""
        parent = self.create_category("Parent")
        self.repository.create("Child", "Circle", b"\x80\x80\x80", parent.uuid)

        self.connection.execute("DELETE FROM category WHERE uuid = ?", (parent.uuid.bytes,))

        self.assertEqual(self.repository.list_all(), [])

    def test_create_rejects_unknown_parent(self) -> None:
        """The database foreign key rejects an unknown parent UUID."""
        from uuid import uuid4

        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.create("Child", "Circle", b"\x80\x80\x80", uuid4())

    def test_list_page_orders_and_rejects_identity_sorting(self) -> None:
        """Category pagination exposes name but not entity or parent UUID."""
        for name in ("Charlie", "Alpha", "Bravo"):
            self.repository.create(name, "Circle", b"\x80\x80\x80", None)

        page = self.repository.list_page(1, 2, "name", False)

        self.assertEqual([category.name for category in page], ["Charlie", "Bravo"])
        for sort_key in ("uuid", "parent_uuid"):
            with self.subTest(sort_key=sort_key):
                with self.assertRaises(ValueError):
                    self.repository.list_page(1, 10, sort_key, True)

    def test_get_tree_returns_roots_with_ordered_descendants(self) -> None:
        leisure = self.create_category("Leisure")
        food = self.create_category("Food")
        restaurants = self.create_category("Restaurants", food)
        groceries = self.create_category("Groceries", food)
        self.create_category("Bakeries", groceries)

        tree = self.repository.get_tree()

        self.assertEqual(self._names(tree), [("Food", [("Groceries", [("Bakeries", [])]), ("Restaurants", [])]), ("Leisure", [])])
        self.assertEqual(tree[0].category, food)
        self.assertEqual(tree[1].category, leisure)
        self.assertEqual(tree[0].children[0].category, groceries)
        self.assertEqual(tree[0].children[1].category, restaurants)

    def test_get_tree_returns_no_nodes_when_there_are_no_categories(self) -> None:
        self.assertEqual(self.repository.get_tree(), [])

    @classmethod
    def _names(cls, nodes: list[CategoryTreeNode]) -> list[tuple[str, list]]:
        return [(node.category.name, cls._names(node.children)) for node in nodes]


if __name__ == "__main__":
    import unittest

    unittest.main()
