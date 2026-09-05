"""Unit tests for shared appearance value types."""

import unittest

from pydantic import TypeAdapter, ValidationError

from app.domain.appearance import Icon


class IconTest(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = TypeAdapter(Icon)

    def test_accepts_prefixed_lucide_and_unicode_icons(self) -> None:
        for icon in ("lucide:WalletCards", "lucide:A" + "1" * 92, "unicode:$", "unicode:R$", "unicode:💰💳"):
            with self.subTest(icon=icon):
                self.assertEqual(self.adapter.validate_python(icon), icon)

    def test_rejects_unsupported_or_empty_icon_formats(self) -> None:
        for icon in ("WalletCards", "💰", "unicode:", "lucide:", "lucide:not-a-name", "lucide:1Wallet"):
            with self.subTest(icon=icon):
                with self.assertRaises(ValidationError):
                    self.adapter.validate_python(icon)

    def test_rejects_unicode_icons_longer_than_three_characters(self) -> None:
        with self.assertRaises(ValidationError):
            self.adapter.validate_python("unicode:ABCD")

    def test_rejects_icons_longer_than_one_hundred_characters(self) -> None:
        self.assertEqual(len("lucide:" + "A" + "1" * 92), 100)
        with self.assertRaises(ValidationError):
            self.adapter.validate_python("lucide:" + "A" + "1" * 93)


if __name__ == "__main__":
    unittest.main()
