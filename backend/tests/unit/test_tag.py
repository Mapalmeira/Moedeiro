"""Unit tests for the tag model."""

import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.ledger.model.tag import Tag


class TagTest(unittest.TestCase):
    def test_accepts_name_at_length_boundaries(self) -> None:
        for name in ("x", "x" * 30):
            with self.subTest(name_length=len(name)):
                tag = Tag(uuid=uuid4(), name=name)
                self.assertEqual(tag.name, name)

    def test_rejects_name_outside_length_limits(self) -> None:
        for name in ("", "x" * 31):
            with self.subTest(name_length=len(name)):
                with self.assertRaises(ValidationError):
                    Tag(uuid=uuid4(), name=name)


if __name__ == "__main__":
    unittest.main()
