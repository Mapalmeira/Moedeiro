"""Unit tests for the registry ledger model."""

import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.registry.model.ledger import Ledger


class RegistryLedgerTest(unittest.TestCase):
    def test_accepts_nonempty_path_without_maximum_length(self) -> None:
        for path in ("x", "x" * 10000):
            with self.subTest(path_length=len(path)):
                ledger = Ledger(uuid=uuid4(), path=path)
                self.assertEqual(ledger.path, path)

    def test_rejects_empty_path(self) -> None:
        with self.assertRaises(ValidationError):
            Ledger(uuid=uuid4(), path="")


if __name__ == "__main__":
    unittest.main()
