"""Unit tests for the ledger-metadata model."""

import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.ledger.model.ledger_metadata import LedgerMetadata


class LedgerMetadataTest(unittest.TestCase):
    def test_accepts_first_schema_version(self) -> None:
        metadata = LedgerMetadata(
            ledger_uuid=uuid4(),
            name="Personal",
            schema_version=1,
            created_at=10,
        )

        self.assertEqual(metadata.schema_version, 1)

    def test_rejects_schema_version_lower_than_one(self) -> None:
        with self.assertRaises(ValidationError):
            LedgerMetadata(
                ledger_uuid=uuid4(),
                name="Personal",
                schema_version=0,
                created_at=10,
            )

    def test_rejects_name_outside_length_limits(self) -> None:
        for name in ("", "x" * 51):
            with self.subTest(name_length=len(name)):
                with self.assertRaises(ValidationError):
                    LedgerMetadata(
                        ledger_uuid=uuid4(),
                        name=name,
                        schema_version=1,
                        created_at=10,
                    )

    def test_accepts_name_at_maximum_length(self) -> None:
        metadata = LedgerMetadata(ledger_uuid=uuid4(), name="x" * 50, schema_version=1, created_at=10)

        self.assertEqual(len(metadata.name), 50)


if __name__ == "__main__":
    unittest.main()
