"""Integration tests for the ledger SQLite transactional wrapper.

Repository behavior is covered separately. These tests focus on shared connection,
explicit commit, rollback and connection ownership.
"""

import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.ledger.repository.account import SqliteAccountRepository
from app.infrastructure.persistence.sqlite.ledger.repository.account_balance_query import SqliteAccountBalanceQueryRepository
from app.infrastructure.persistence.sqlite.ledger.repository.budget import SqliteBudgetRepository
from app.infrastructure.persistence.sqlite.ledger.repository.budget_status_query import SqliteBudgetStatusQueryRepository
from app.infrastructure.persistence.sqlite.ledger.repository.cash_flow_query import SqliteCashFlowQueryRepository
from app.infrastructure.persistence.sqlite.ledger.repository.category import SqliteCategoryRepository
from app.infrastructure.persistence.sqlite.ledger.repository.currency import SqliteCurrencyRepository
from app.infrastructure.persistence.sqlite.ledger.repository.financial_event import SqliteFinancialEventRepository
from app.infrastructure.persistence.sqlite.ledger.repository.financial_movement import SqliteFinancialMovementRepository
from app.infrastructure.persistence.sqlite.ledger.repository.ledger_metadata import SqliteLedgerMetadataRepository
from app.infrastructure.persistence.sqlite.ledger.unit_of_work import SqliteLedgerUnitOfWork


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class SqliteLedgerUnitOfWorkTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.database = SqliteDatabase(Path(self.temporary_directory.name) / "ledger.sqlite")
        connection = self.database.get_connection()
        try:
            connection.executescript(SCHEMA_PATH.read_text())
            connection.commit()
        finally:
            connection.close()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_repositories_share_the_unit_of_work_connection(self) -> None:
        """Every ledger repository participates in the same transaction."""
        with SqliteLedgerUnitOfWork(self.database) as unit_of_work:
            account_repository = unit_of_work.account_repository
            account_balance_query_repository = unit_of_work.account_balance_query_repository
            budget_repository = unit_of_work.budget_repository
            budget_status_query_repository = unit_of_work.budget_status_query_repository
            cash_flow_query_repository = unit_of_work.cash_flow_query_repository
            category_repository = unit_of_work.category_repository
            currency_repository = unit_of_work.currency_repository
            financial_movement_repository = unit_of_work.financial_movement_repository
            ledger_metadata_repository = unit_of_work.ledger_metadata_repository
            financial_event_repository = unit_of_work.financial_event_repository
            assert isinstance(account_repository, SqliteAccountRepository)
            assert isinstance(account_balance_query_repository, SqliteAccountBalanceQueryRepository)
            assert isinstance(budget_repository, SqliteBudgetRepository)
            assert isinstance(budget_status_query_repository, SqliteBudgetStatusQueryRepository)
            assert isinstance(cash_flow_query_repository, SqliteCashFlowQueryRepository)
            assert isinstance(category_repository, SqliteCategoryRepository)
            assert isinstance(currency_repository, SqliteCurrencyRepository)
            assert isinstance(financial_movement_repository, SqliteFinancialMovementRepository)
            assert isinstance(ledger_metadata_repository, SqliteLedgerMetadataRepository)
            assert isinstance(financial_event_repository, SqliteFinancialEventRepository)
            repositories = [
                account_repository,
                account_balance_query_repository,
                budget_repository,
                budget_status_query_repository,
                cash_flow_query_repository,
                category_repository,
                currency_repository,
                financial_movement_repository,
                ledger_metadata_repository,
                financial_event_repository,
            ]

            for repository in repositories:
                with self.subTest(repository_type=type(repository).__name__):
                    self.assertIs(repository.connection, unit_of_work.connection)

    def test_commit_persists_changes_after_scope_exit(self) -> None:
        """Only an explicit commit makes changes visible to a later operation."""
        ledger_uuid = uuid4()
        with SqliteLedgerUnitOfWork(self.database) as unit_of_work:
            unit_of_work.ledger_metadata_repository.create(ledger_uuid, "Personal", 1)
            unit_of_work.commit()

        with SqliteLedgerUnitOfWork(self.database) as unit_of_work:
            metadata = unit_of_work.ledger_metadata_repository.get()
            assert metadata is not None
            self.assertEqual(metadata.ledger_uuid, ledger_uuid)

    def test_exit_without_commit_rolls_back_changes(self) -> None:
        """Leaving the scope discards pending writes."""
        with SqliteLedgerUnitOfWork(self.database) as unit_of_work:
            unit_of_work.currency_repository.create(
                "Temporary", None, None, 2, "Circle", b"\x80\x80\x80"
            )

        with SqliteLedgerUnitOfWork(self.database) as unit_of_work:
            self.assertEqual(unit_of_work.currency_repository.list_all(), [])

    def test_exception_rolls_back_and_propagates(self) -> None:
        """An exceptional exit discards pending writes without suppressing the error."""
        with self.assertRaisesRegex(RuntimeError, "expected failure"):
            with SqliteLedgerUnitOfWork(self.database) as unit_of_work:
                unit_of_work.currency_repository.create(
                    "Temporary", None, None, 2, "Circle", b"\x80\x80\x80"
                )
                raise RuntimeError("expected failure")

        with SqliteLedgerUnitOfWork(self.database) as unit_of_work:
            self.assertEqual(unit_of_work.currency_repository.list_all(), [])

    def test_exit_closes_the_owned_connection(self) -> None:
        """The connection cannot be reused after the transactional scope ends."""
        with SqliteLedgerUnitOfWork(self.database) as unit_of_work:
            connection = unit_of_work.connection

        with self.assertRaises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")


if __name__ == "__main__":
    unittest.main()
