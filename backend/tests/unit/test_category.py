"""Unit tests for the category model."""

import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.ledger.model.category import Category


class CategoryTest(unittest.TestCase):
    def test_accepts_category_with_or_without_parent(self) -> None:
        root = Category(uuid=uuid4(), name="Food", icon="lucide:Utensils", color_code=b"\xff\x80\x00")
        child = Category(uuid=uuid4(), name="Restaurants", icon="lucide:Store", color_code=b"\xff\x80\x00", parent_uuid=root.uuid)

        self.assertIsNone(root.parent_uuid)
        self.assertEqual(child.parent_uuid, root.uuid)
        self.assertEqual(root.color_code, b"\xff\x80\x00")

    def test_rejects_name_outside_length_limits(self) -> None:
        for name in ("", "x" * 31):
            with self.subTest(name_length=len(name)):
                with self.assertRaises(ValidationError):
                    Category(uuid=uuid4(), name=name, icon="lucide:Circle", color_code=b"\x00\x00\x00")

    def test_rejects_icon_and_color_outside_limits(self) -> None:
        invalid_values = (
            ("icon", "lucide:" + "x" * 94),
            ("color_code", b"\x00\x00"),
            ("color_code", b"\x00" * 4),
        )
        for field, value in invalid_values:
            with self.subTest(field=field, length=len(value)):
                values = {"uuid": uuid4(), "name": "Food", "icon": "lucide:Circle", "color_code": b"\x00\x00\x00"}
                values[field] = value
                with self.assertRaises(ValidationError):
                    Category(**values)

    def test_accepts_prefixed_lucide_and_unicode_icons(self) -> None:
        unicode_icon = Category(uuid=uuid4(), name="Food", icon="unicode:💰💳", color_code=b"\x00\x00\x00")
        lucide_icon = Category(uuid=uuid4(), name="Travel", icon="lucide:Landmark", color_code=b"\x00\x00\x00")

        self.assertEqual(unicode_icon.icon, "unicode:💰💳")
        self.assertEqual(lucide_icon.icon, "lucide:Landmark")

    def test_rejects_icons_without_supported_prefix_or_invalid_payload(self) -> None:
        for icon in ("Circle", "💰", "unicode:", "unicode:ABCD", "lucide:", "lucide:not-a-name"):
            with self.subTest(icon=icon):
                with self.assertRaises(ValidationError):
                    Category(uuid=uuid4(), name="Food", icon=icon, color_code=b"\x00\x00\x00")
