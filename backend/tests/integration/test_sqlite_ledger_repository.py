"""Integration tests for the registry SQLite ledger repository."""

import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pydantic import ValidationError

from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.registry.repository.ledger import (
    SqliteLedgerRepository,
)
from app.infrastructure.persistence.sqlite.registry.repository.ledger_token import (
    SqliteLedgerTokenRepository,
)


SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
)


class SqliteLedgerRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "registry.sqlite"
        self.connection = SqliteDatabase(database_path).get_connection()
        self.connection.executescript(SCHEMA_PATH.read_text())
        self.repository = SqliteLedgerRepository(self.connection)

    def tearDown(self) -> None:
        self.connection.close()
        self.temporary_directory.cleanup()

    def test_create_can_be_read_by_uuid_and_path(self) -> None:
        """create persists a generated UUID and the supplied path."""
        self.repository.create("ledger.sqlite")

        ledger = self.repository.get_by_path("ledger.sqlite")

        self.assertIsNotNone(ledger)
        assert ledger is not None
        self.assertEqual(self.repository.get(ledger.uuid), ledger)

    def test_get_returns_none_when_ledger_does_not_exist(self) -> None:
        """get and get_by_path represent an absent row with None."""
        self.repository.create("ledger.sqlite")
        ledger = self.repository.get_by_path("ledger.sqlite")
        assert ledger is not None
        self.repository.delete(ledger.uuid)

        self.assertIsNone(self.repository.get(ledger.uuid))
        self.assertIsNone(self.repository.get_by_path("ledger.sqlite"))

    def test_update_path_changes_only_the_selected_ledger(self) -> None:
        """update_path keeps the UUID and changes only the requested row."""
        self.repository.create("first.sqlite")
        self.repository.create("second.sqlite")
        first = self.repository.get_by_path("first.sqlite")
        second = self.repository.get_by_path("second.sqlite")
        assert first is not None
        assert second is not None

        self.repository.update_path(first.uuid, "updated.sqlite")

        self.assertIsNone(self.repository.get_by_path("first.sqlite"))
        self.assertEqual(
            self.repository.get(first.uuid),
            first.model_copy(update={"path": "updated.sqlite"}),
        )
        self.assertEqual(self.repository.get(second.uuid), second)

    def test_list_all_returns_every_ledger_without_promising_order(self) -> None:
        """list_all returns the complete collection; ordering is unspecified."""
        self.repository.create("first.sqlite")
        self.repository.create("second.sqlite")

        ledgers = self.repository.list_all()

        self.assertCountEqual(
            [ledger.path for ledger in ledgers],
            ["first.sqlite", "second.sqlite"],
        )

    def test_delete_ledger_cascades_to_its_tokens(self) -> None:
        """The repository uses a connection with SQLite foreign keys enabled."""
        token_repository = SqliteLedgerTokenRepository(self.connection)
        self.repository.create("ledger.sqlite")
        ledger = self.repository.get_by_path("ledger.sqlite")
        assert ledger is not None
        token_repository.create(ledger.uuid, "token-hash", None, 10)
        token = token_repository.get_by_token_hash("token-hash")
        assert token is not None

        self.repository.delete(ledger.uuid)

        self.assertIsNone(token_repository.get(token.uuid))

    def test_repository_does_not_commit_its_own_changes(self) -> None:
        """Transaction ownership remains with the unit of work."""
        self.repository.create("ledger.sqlite")

        self.connection.rollback()

        self.assertIsNone(self.repository.get_by_path("ledger.sqlite"))

    def test_create_rejects_path_longer_than_model_limit(self) -> None:
        """The domain model's 4096-character path limit is enforced on create."""
        with self.assertRaises(ValidationError):
            self.repository.create("x" * 4097)

    def test_update_rejects_path_longer_than_model_limit(self) -> None:
        """The domain model's path limit is also enforced on update."""
        self.repository.create("ledger.sqlite")
        ledger = self.repository.get_by_path("ledger.sqlite")
        assert ledger is not None

        with self.assertRaises(ValidationError):
            self.repository.update_path(ledger.uuid, "x" * 4097)

    def test_database_rejects_duplicate_paths(self) -> None:
        """The schema's unique path constraint is visible through the repository."""
        self.repository.create("ledger.sqlite")

        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.create("ledger.sqlite")


if __name__ == "__main__":
    unittest.main()
