"""SQLite transactional wrapper whose ledger repositories share one connection."""

import sqlite3
from typing import Self

from app.application.ledger.unit_of_work import LedgerUnitOfWork
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


class SqliteLedgerUnitOfWork(LedgerUnitOfWork):
    def __init__(self, database: SqliteDatabase, max_page_size: int):
        self.database = database
        self.max_page_size = max_page_size

    def __enter__(self) -> Self:
        self.connection: sqlite3.Connection = self.database.get_connection()
        self._transaction_start_total_changes = self.connection.total_changes

        self.account_repository = SqliteAccountRepository(self.connection, self.max_page_size)
        self.account_balance_query_repository = SqliteAccountBalanceQueryRepository(self.connection)
        self.budget_repository = SqliteBudgetRepository(self.connection, self.max_page_size)
        self.budget_status_query_repository = SqliteBudgetStatusQueryRepository(self.connection)
        self.cash_flow_query_repository = SqliteCashFlowQueryRepository(self.connection)
        self.category_repository = SqliteCategoryRepository(self.connection, self.max_page_size)
        self.currency_repository = SqliteCurrencyRepository(self.connection, self.max_page_size)
        self.financial_movement_repository = SqliteFinancialMovementRepository(self.connection)
        self.ledger_metadata_repository = SqliteLedgerMetadataRepository(self.connection)
        self.financial_event_repository = SqliteFinancialEventRepository(self.connection, self.max_page_size)

        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        try:
            self.rollback()
        finally:
            self.connection.close()

    def commit(self) -> None:
        if self.connection.total_changes > self._transaction_start_total_changes:
            self.connection.execute("UPDATE ledger_metadata SET revision = revision + 1 WHERE singleton = 1")
        self.connection.commit()
        self._transaction_start_total_changes = self.connection.total_changes

    def rollback(self) -> None:
        self.connection.rollback()
        self._transaction_start_total_changes = self.connection.total_changes
