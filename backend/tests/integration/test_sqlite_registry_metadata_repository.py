import sqlite3

from pydantic import ValidationError

from app.infrastructure.persistence.sqlite.registry.repository.registry_metadata import SqliteRegistryMetadataRepository
from tests.integration.registry_repository_test_case import RegistryRepositoryTestCase


class SqliteRegistryMetadataRepositoryTest(RegistryRepositoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repository = SqliteRegistryMetadataRepository(self.connection)

    def test_create_can_be_read_and_updated(self) -> None:
        metadata = self.repository.create(1)

        self.assertEqual(self.repository.get(), metadata)
        self.repository.update_schema_version(2)
        updated = self.repository.get()
        assert updated is not None
        self.assertEqual(updated.schema_version, 2)

    def test_get_returns_none_before_creation(self) -> None:
        self.assertIsNone(self.repository.get())

    def test_create_and_update_validate_the_version(self) -> None:
        with self.assertRaises(ValidationError):
            self.repository.create(0)

        self.repository.create(1)
        with self.assertRaises(ValidationError):
            self.repository.update_schema_version(0)

    def test_database_allows_only_one_metadata_row(self) -> None:
        self.repository.create(1)

        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.create(2)

    def test_repository_does_not_commit_its_changes(self) -> None:
        self.repository.create(1)

        self.connection.rollback()

        self.assertIsNone(self.repository.get())


if __name__ == "__main__":
    import unittest

    unittest.main()
