"""Unit tests for the category tree node model."""

import unittest
from uuid import uuid4

from app.domain.ledger.model.category import Category
from app.domain.ledger.model.category_tree_node import CategoryTreeNode


class CategoryTreeNodeTest(unittest.TestCase):
    def test_accepts_nested_categories(self) -> None:
        root = Category(uuid=uuid4(), name="Food", icon="lucide:Utensils", color_code=b"\xff\x80\x00")
        child = Category(uuid=uuid4(), name="Restaurants", icon="lucide:Store", color_code=b"\xff\x80\x00", parent_uuid=root.uuid)

        tree = CategoryTreeNode(category=root, children=[CategoryTreeNode(category=child)])

        self.assertEqual(tree.category, root)
        self.assertEqual(tree.children[0].category, child)

    def test_children_default_to_an_independent_empty_list(self) -> None:
        root = Category(uuid=uuid4(), name="Food", icon="lucide:Utensils", color_code=b"\xff\x80\x00")
        first = CategoryTreeNode(category=root)
        second = CategoryTreeNode(category=root)

        first.children.append(CategoryTreeNode(category=root))

        self.assertEqual(second.children, [])
