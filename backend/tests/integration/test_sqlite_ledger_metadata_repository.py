"""Integration tests for the ledger SQLite metadata repository."""

import sqlite3
from time import time
from uuid import uuid4

from pydantic import ValidationError

from app.infrastructure.persistence.sqlite.ledger.repository.ledger_metadata import SqliteLedgerMetadataRepository
from tests.integration.ledger_repository_test_case import LedgerRepositoryTestCase


class SqliteLedgerMetadataRepositoryTest(LedgerRepositoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repository = SqliteLedgerMetadataRepository(self.connection)

    def test_get_returns_none_before_metadata_creation(self) -> None:
        """An uninitialized ledger has no metadata row."""
        self.assertIsNone(self.repository.get())

    def test_create_preserves_ledger_identity_and_sets_creation_time(self) -> None:
        """Metadata uses the registry ledger UUID and records its creation time."""
        ledger_uuid = uuid4()
        before_creation = int(time())

        self.repository.create(ledger_uuid, "Personal", 1)

        after_creation = int(time())
        metadata = self.repository.get()
        assert metadata is not None
        self.assertEqual(metadata.ledger_uuid, ledger_uuid)
        self.assertEqual(metadata.name, "Personal")
        self.assertEqual(metadata.schema_version, 1)
        self.assertGreaterEqual(metadata.created_at, before_creation)
        self.assertLessEqual(metadata.created_at, after_creation)

    def test_updates_name_and_schema_version_without_changing_identity(self) -> None:
        """Mutable metadata fields do not replace ledger identity or creation time."""
        ledger_uuid = uuid4()
        self.repository.create(ledger_uuid, "Personal", 1)
        original = self.repository.get()
        assert original is not None

        self.repository.update_name("Family")
        self.repository.update_schema_version(2)

        updated = self.repository.get()
        assert updated is not None
        self.assertEqual(updated.ledger_uuid, ledger_uuid)
        self.assertEqual(updated.created_at, original.created_at)
        self.assertEqual(updated.name, "Family")
        self.assertEqual(updated.schema_version, 2)

    def test_create_and_updates_validate_model_constraints(self) -> None:
        """Metadata operations enforce name and schema-version constraints."""
        with self.assertRaises(ValidationError):
            self.repository.create(uuid4(), "", 1)
        with self.assertRaises(ValidationError):
            self.repository.create(uuid4(), "Personal", 0)

        self.repository.create(uuid4(), "Personal", 1)
        with self.assertRaises(ValidationError):
            self.repository.update_name("x" * 31)
        with self.assertRaises(ValidationError):
            self.repository.update_schema_version(0)

    def test_database_allows_only_one_metadata_row(self) -> None:
        """The singleton key prevents a second metadata record."""
        self.repository.create(uuid4(), "Personal", 1)

        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.create(uuid4(), "Other", 1)

    def test_repository_does_not_commit_its_changes(self) -> None:
        """Metadata creation remains pending until the unit of work commits."""
        self.repository.create(uuid4(), "Personal", 1)

        self.connection.rollback()

        self.assertIsNone(self.repository.get())


if __name__ == "__main__":
    import unittest

    unittest.main()
