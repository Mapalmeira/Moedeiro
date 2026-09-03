import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.domain.ledger.model.account import Account
from app.domain.ledger.model.budget import Budget
from app.domain.ledger.model.category import Category
from app.domain.ledger.model.currency import Currency
from app.domain.ledger.model.financial_event import FinancialEvent, FinancialEventType
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.ledger.repository.account import SqliteAccountRepository
from app.infrastructure.persistence.sqlite.ledger.repository.budget import SqliteBudgetRepository
from app.infrastructure.persistence.sqlite.ledger.repository.category import SqliteCategoryRepository
from app.infrastructure.persistence.sqlite.ledger.repository.currency import SqliteCurrencyRepository
from app.infrastructure.persistence.sqlite.ledger.repository.financial_event import SqliteFinancialEventRepository


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class LedgerRepositoryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "ledger.sqlite"
        self.connection = SqliteDatabase(database_path).get_connection()
        self.connection.executescript(SCHEMA_PATH.read_text())

    def tearDown(self) -> None:
        self.connection.close()
        self.temporary_directory.cleanup()

    def create_currency(self, name: str = "Real") -> Currency:
        repository = SqliteCurrencyRepository(self.connection)
        return repository.create(name, "R$", None, 2, "R$", b"\x80\x80\x80")

    def create_category(self, name: str = "Food", parent: Category | None = None) -> Category:
        repository = SqliteCategoryRepository(self.connection)
        return repository.create(name, "Circle", b"\x80\x80\x80", None if parent is None else parent.uuid)

    def create_account(self, name: str = "Checking", currency: Currency | None = None) -> Account:
        selected_currency = currency or self.create_currency()
        repository = SqliteAccountRepository(self.connection)
        return repository.create(name, None, selected_currency.uuid, "WalletCards", b"\x80\x80\x80")

    def create_event(self, description: str = "Purchase", type: FinancialEventType = "TRANSACTION", occurred_at: int = 10) -> FinancialEvent:
        repository = SqliteFinancialEventRepository(self.connection)
        return repository.create(occurred_at, description, type)

    def create_budget(self, name: str = "Monthly", currency: Currency | None = None, category: Category | None = None) -> Budget:
        selected_currency = currency or self.create_currency()
        selected_category = category or self.create_category()
        repository = SqliteBudgetRepository(self.connection)
        return repository.create(selected_category.uuid, selected_currency.uuid, 10, 20, name, "Monthly spending", 100, "ReceiptText", b"\x80\x80\x80")
