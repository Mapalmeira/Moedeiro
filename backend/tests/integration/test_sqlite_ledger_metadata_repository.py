"""Integration tests for the ledger SQLite metadata repository."""

import sqlite3
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

    def test_create_preserves_ledger_identity_and_creation_time(self) -> None:
        """Metadata uses the ledger UUID and timestamp supplied by its creator."""
        ledger_uuid = uuid4()

        created_metadata = self.repository.create(ledger_uuid, 1, 100)

        metadata = self.repository.get()
        assert metadata is not None
        self.assertEqual(created_metadata, metadata)
        self.assertEqual(metadata.ledger_uuid, ledger_uuid)
        self.assertEqual(metadata.schema_version, 1)
        self.assertEqual(metadata.revision, 0)
        self.assertEqual(metadata.created_at, 100)

    def test_updates_schema_version_without_changing_identity(self) -> None:
        ledger_uuid = uuid4()
        self.repository.create(ledger_uuid, 1, 100)
        original = self.repository.get()
        assert original is not None

        self.repository.update_schema_version(2)

        updated = self.repository.get()
        assert updated is not None
        self.assertEqual(updated.ledger_uuid, ledger_uuid)
        self.assertEqual(updated.created_at, original.created_at)
        self.assertEqual(updated.schema_version, 2)
        self.assertEqual(updated.revision, original.revision)

    def test_create_and_update_validate_schema_version(self) -> None:
        with self.assertRaises(ValidationError):
            self.repository.create(uuid4(), 0, 100)

        self.repository.create(uuid4(), 1, 100)
        with self.assertRaises(ValidationError):
            self.repository.update_schema_version(0)

    def test_database_allows_only_one_metadata_row(self) -> None:
        """The singleton key prevents a second metadata record."""
        self.repository.create(uuid4(), 1, 100)

        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.create(uuid4(), 1, 100)

    def test_repository_does_not_commit_its_changes(self) -> None:
        """Metadata creation remains pending until the unit of work commits."""
        self.repository.create(uuid4(), 1, 100)

        self.connection.rollback()

        self.assertIsNone(self.repository.get())


if __name__ == "__main__":
    import unittest

    unittest.main()
