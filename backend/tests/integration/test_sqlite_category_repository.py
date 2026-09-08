"""Integration tests for the ledger SQLite category repository."""

import sqlite3
from uuid import uuid4

from pydantic import ValidationError

from app.application.ledger.exceptions import CategoryDepthExceededError, CategoryTreeSizeExceededError, InvalidCategoryHierarchyError
from app.domain.ledger.model.category_tree_node import CategoryTreeNode
from app.infrastructure.persistence.sqlite.ledger.repository.category import SqliteCategoryRepository
from app.infrastructure.persistence.sqlite.ledger.repository.financial_movement import SqliteFinancialMovementRepository
from tests.integration.ledger_repository_test_case import LedgerRepositoryTestCase


class SqliteCategoryRepositoryTest(LedgerRepositoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repository = SqliteCategoryRepository(self.connection)

    def test_create_get_and_update_parent(self) -> None:
        """A category can acquire and clear an existing parent."""
        parent = self.create_category("Parent")
        child = self.repository.create("Child", "lucide:Circle", b"\x80\x80\x80", None)

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

        self.repository.update_icon(category.uuid, "lucide:Utensils")
        self.repository.update_color_code(category.uuid, b"\xff\x80\x00")

        updated = self.repository.get(category.uuid)
        assert updated is not None
        self.assertEqual(updated.icon, "lucide:Utensils")
        self.assertEqual(updated.color_code, b"\xff\x80\x00")
        self.assertEqual(updated.parent_uuid, category.parent_uuid)

    def test_get_many_returns_only_requested_categories(self) -> None:
        food = self.create_category("Food")
        leisure = self.create_category("Leisure")
        self.create_category("Transport")

        categories = self.repository.get_many([leisure.uuid, food.uuid, leisure.uuid, uuid4()])

        self.assertEqual({category.uuid for category in categories}, {food.uuid, leisure.uuid})
        self.assertEqual(self.repository.get_many([]), [])

    def test_get_by_name_returns_the_matching_category(self) -> None:
        food = self.create_category("Food")
        self.create_category("Transport")

        self.assertEqual(self.repository.get_by_name("Food"), food)
        self.assertIsNone(self.repository.get_by_name("Missing"))

    def test_schema_rejects_duplicate_category_names(self) -> None:
        self.create_category("Food")

        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.create("Food", "lucide:Circle", b"\x80\x80\x80", None)

    def test_update_name_validates_model_limit(self) -> None:
        """Category names are validated before an update is executed."""
        category = self.create_category()

        with self.assertRaises(ValidationError):
            self.repository.update_name(category.uuid, "x" * 31)

    def test_deleting_parent_cascades_to_children(self) -> None:
        """The schema relation applies its configured parent cascade."""
        parent = self.create_category("Parent")
        child = self.repository.create("Child", "lucide:Circle", b"\x80\x80\x80", parent.uuid)

        self.repository.delete(parent.uuid)

        self.assertIsNone(self.repository.get(parent.uuid))
        self.assertIsNone(self.repository.get(child.uuid))

    def test_is_in_use_considers_movements_and_budgets_in_the_whole_subtree(self) -> None:
        movement_parent = self.create_category("Movement parent")
        movement_child = self.create_category("Movement child", movement_parent)
        budget_parent = self.create_category("Budget parent")
        budget_child = self.create_category("Budget child", budget_parent)
        unused = self.create_category("Unused")
        currency = self.create_currency()
        account = self.create_account(currency=currency)
        event = self.create_event()
        SqliteFinancialMovementRepository(self.connection).create(event.uuid, account.uuid, movement_child.uuid, -100, None)
        self.create_budget(account=account, category=budget_child)

        self.assertTrue(self.repository.is_in_use(movement_parent.uuid))
        self.assertTrue(self.repository.is_in_use(budget_parent.uuid))
        self.assertFalse(self.repository.is_in_use(unused.uuid))

    def test_create_rejects_unknown_parent(self) -> None:
        """The database foreign key rejects an unknown parent UUID."""
        from uuid import uuid4

        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.create("Child", "lucide:Circle", b"\x80\x80\x80", uuid4())

    def test_create_rejects_a_sixth_category_level(self) -> None:
        parent = None
        for level in range(5):
            parent = self.repository.create(f"Level {level}", "lucide:Circle", b"\x80\x80\x80", None if parent is None else parent.uuid)
        assert parent is not None

        with self.assertRaises(CategoryDepthExceededError):
            self.repository.create("Too deep", "lucide:Circle", b"\x80\x80\x80", parent.uuid)

        self.assertEqual(self._count(self.repository.get_tree(1000)), 5)

    def test_update_parent_rejects_cycles_and_subtrees_that_exceed_the_depth_limit(self) -> None:
        root = self.create_category("Root")
        source = self.create_category("Source", root)
        child = self.create_category("Child", source)
        self.create_category("Grandchild", child)
        target_root = self.create_category("Target root")
        target_child = self.create_category("Target child", target_root)
        target_grandchild = self.create_category("Target grandchild", target_child)

        with self.assertRaises(InvalidCategoryHierarchyError):
            self.repository.update_parent(root.uuid, child.uuid)
        with self.assertRaises(CategoryDepthExceededError):
            self.repository.update_parent(source.uuid, target_grandchild.uuid)

        stored_root = self.repository.get(root.uuid)
        stored_source = self.repository.get(source.uuid)
        assert stored_root is not None
        assert stored_source is not None
        self.assertIsNone(stored_root.parent_uuid)
        self.assertEqual(stored_source.parent_uuid, root.uuid)

    def test_update_parent_allows_the_fifth_level(self) -> None:
        root = self.create_category("Root")
        second = self.create_category("Second", root)
        third = self.create_category("Third", second)
        fourth = self.create_category("Fourth", third)
        child = self.create_category("Child")

        self.repository.update_parent(child.uuid, fourth.uuid)

        stored_child = self.repository.get(child.uuid)
        assert stored_child is not None
        self.assertEqual(stored_child.parent_uuid, fourth.uuid)

    def test_count_and_tree_read_limit_are_applied(self) -> None:
        self.repository.create("First", "lucide:Circle", b"\x80\x80\x80", None)
        self.repository.create("Second", "lucide:Circle", b"\x80\x80\x80", None)

        self.assertEqual(self.repository.count(), 2)
        with self.assertRaises(CategoryTreeSizeExceededError):
            self.repository.get_tree(1)

    def test_get_tree_returns_roots_with_ordered_descendants(self) -> None:
        leisure = self.create_category("Leisure")
        food = self.create_category("Food")
        restaurants = self.create_category("Restaurants", food)
        groceries = self.create_category("Groceries", food)
        self.create_category("Bakeries", groceries)

        tree = self.repository.get_tree(1000)

        self.assertEqual(self._names(tree), [("Food", [("Groceries", [("Bakeries", [])]), ("Restaurants", [])]), ("Leisure", [])])
        self.assertEqual(tree[0].category, food)
        self.assertEqual(tree[1].category, leisure)
        self.assertEqual(tree[0].children[0].category, groceries)
        self.assertEqual(tree[0].children[1].category, restaurants)

    def test_get_tree_returns_no_nodes_when_there_are_no_categories(self) -> None:
        self.assertEqual(self.repository.get_tree(1000), [])

    @classmethod
    def _names(cls, nodes: list[CategoryTreeNode]) -> list[tuple[str, list]]:
        return [(node.category.name, cls._names(node.children)) for node in nodes]

    @classmethod
    def _count(cls, nodes: list[CategoryTreeNode]) -> int:
        return sum(1 + cls._count(node.children) for node in nodes)


if __name__ == "__main__":
    import unittest

    unittest.main()
