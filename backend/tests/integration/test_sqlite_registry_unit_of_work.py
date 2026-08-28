"""Integration tests for the registry SQLite unit of work.

These tests exercise the transactional wrapper against a real temporary SQLite
database. Repository behavior is covered separately; this suite focuses on
connection ownership, commit and rollback.
"""

import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.registry.repository.ledger import SqliteLedgerRepository
from app.infrastructure.persistence.sqlite.registry.repository.ledger_token import SqliteLedgerTokenRepository
from app.infrastructure.persistence.sqlite.registry.unit_of_work import (
    SqliteRegistryUnitOfWork,
)


SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
)


class SqliteRegistryUnitOfWorkTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.database = SqliteDatabase(
            Path(self.temporary_directory.name) / "registry.sqlite"
        )

        connection = self.database.get_connection()
        try:
            connection.executescript(SCHEMA_PATH.read_text())
            connection.commit()
        finally:
            connection.close()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_enter_returns_the_opened_unit_of_work(self) -> None:
        """The value bound by with is the same unit-of-work instance."""
        unit_of_work = SqliteRegistryUnitOfWork(self.database)

        with unit_of_work as entered_unit_of_work:
            self.assertIs(entered_unit_of_work, unit_of_work)

    def test_repositories_share_the_unit_of_work_connection(self) -> None:
        """All registry operations in one scope participate in one transaction."""
        with SqliteRegistryUnitOfWork(self.database) as unit_of_work:
            ledger_repository = unit_of_work.ledger_repository
            ledger_token_repository = unit_of_work.ledger_token_repository
            assert isinstance(ledger_repository, SqliteLedgerRepository)
            assert isinstance(ledger_token_repository, SqliteLedgerTokenRepository)

            self.assertIs(
                ledger_repository.connection,
                unit_of_work.connection,
            )
            self.assertIs(
                ledger_token_repository.connection,
                unit_of_work.connection,
            )

    def test_commit_persists_changes_after_the_scope_ends(self) -> None:
        """An explicit commit makes changes visible to a later connection."""
        with SqliteRegistryUnitOfWork(self.database) as unit_of_work:
            unit_of_work.ledger_repository.create("committed.sqlite")
            unit_of_work.commit()

        with SqliteRegistryUnitOfWork(self.database) as verification_unit_of_work:
            ledger = verification_unit_of_work.ledger_repository.get_by_path(
                "committed.sqlite"
            )
            self.assertIsNotNone(ledger)

    def test_explicit_rollback_discards_pending_changes(self) -> None:
        """rollback can cancel the current transaction before leaving the scope."""
        with SqliteRegistryUnitOfWork(self.database) as unit_of_work:
            unit_of_work.ledger_repository.create("rolled-back.sqlite")
            unit_of_work.rollback()

            ledger = unit_of_work.ledger_repository.get_by_path(
                "rolled-back.sqlite"
            )
            self.assertIsNone(ledger)

    def test_exit_without_commit_rolls_back_pending_changes(self) -> None:
        """Leaving a scope never commits changes implicitly."""
        with SqliteRegistryUnitOfWork(self.database) as unit_of_work:
            unit_of_work.ledger_repository.create("uncommitted.sqlite")

        with SqliteRegistryUnitOfWork(self.database) as verification_unit_of_work:
            ledger = verification_unit_of_work.ledger_repository.get_by_path(
                "uncommitted.sqlite"
            )
            self.assertIsNone(ledger)

    def test_exit_closes_the_owned_connection(self) -> None:
        """The SQLite connection cannot be reused after its scope ends."""
        with SqliteRegistryUnitOfWork(self.database) as unit_of_work:
            connection = unit_of_work.connection

        with self.assertRaises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")

    def test_exception_is_propagated_to_the_caller(self) -> None:
        """The context manager does not suppress application exceptions."""
        with self.assertRaisesRegex(RuntimeError, "expected failure"):
            with SqliteRegistryUnitOfWork(self.database):
                raise RuntimeError("expected failure")

    def test_exception_rolls_back_pending_changes(self) -> None:
        """An exceptional exit discards every uncommitted operation in the scope."""
        with self.assertRaises(RuntimeError):
            with SqliteRegistryUnitOfWork(self.database) as unit_of_work:
                unit_of_work.ledger_repository.create("failing.sqlite")
                raise RuntimeError("expected failure")

        with SqliteRegistryUnitOfWork(self.database) as verification_unit_of_work:
            ledger = verification_unit_of_work.ledger_repository.get_by_path(
                "failing.sqlite"
            )
            self.assertIsNone(ledger)


if __name__ == "__main__":
    unittest.main()
