"""Unit tests for the registry ledger model."""

import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.registry.model.ledger import Ledger


class RegistryLedgerTest(unittest.TestCase):
    def test_does_not_validate_backend_managed_path(self) -> None:
        for path in ("", "x" * 10000):
            with self.subTest(path_length=len(path)):
                ledger = Ledger(uuid=uuid4(), name="Main ledger", path=path, icon="BookOpen", color_code=b"\x00\x00\x00")
                self.assertEqual(ledger.path, path)

    def test_rejects_name_outside_limits(self) -> None:
        for name in ("", "x" * 51):
            with self.subTest(length=len(name)):
                with self.assertRaises(ValidationError):
                    Ledger(uuid=uuid4(), name=name, path="ledger.sqlite", icon="BookOpen", color_code=b"\x00\x00\x00")

    def test_rejects_icon_and_color_outside_limits(self) -> None:
        invalid_values = (("icon", "x" * 51), ("color_code", b"\x00\x00"), ("color_code", b"\x00" * 4))
        for field, value in invalid_values:
            with self.subTest(field=field, length=len(value)):
                values = {"uuid": uuid4(), "name": "Main ledger", "path": "ledger.sqlite", "icon": "BookOpen", "color_code": b"\x00\x00\x00"}
                values[field] = value
                with self.assertRaises(ValidationError):
                    Ledger(**values)


if __name__ == "__main__":
    unittest.main()
