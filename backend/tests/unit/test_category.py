"""Unit tests for the category model."""

import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.ledger.model.category import Category


class CategoryTest(unittest.TestCase):
    def test_accepts_category_with_or_without_parent(self) -> None:
        root = Category(uuid=uuid4(), name="Food")
        child = Category(uuid=uuid4(), name="Restaurants", parent_uuid=root.uuid)

        self.assertIsNone(root.parent_uuid)
        self.assertEqual(child.parent_uuid, root.uuid)

    def test_rejects_name_outside_length_limits(self) -> None:
        for name in ("", "x" * 31):
            with self.subTest(name_length=len(name)):
                with self.assertRaises(ValidationError):
                    Category(uuid=uuid4(), name=name)


if __name__ == "__main__":
    unittest.main()
