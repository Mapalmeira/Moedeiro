import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.domain.ledger.model.account import Account
from app.domain.ledger.model.budget import Budget
from app.domain.ledger.model.category import Category
from app.domain.ledger.model.currency import Currency
from app.domain.ledger.model.tag import Tag
from app.domain.ledger.model.transaction_event import TransactionEvent, TransactionEventType
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.ledger.repository.account import SqliteAccountRepository
from app.infrastructure.persistence.sqlite.ledger.repository.budget import SqliteBudgetRepository
from app.infrastructure.persistence.sqlite.ledger.repository.category import SqliteCategoryRepository
from app.infrastructure.persistence.sqlite.ledger.repository.currency import SqliteCurrencyRepository
from app.infrastructure.persistence.sqlite.ledger.repository.tag import SqliteTagRepository
from app.infrastructure.persistence.sqlite.ledger.repository.transaction_event import SqliteTransactionEventRepository


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
        repository.create(name, "R$", None, 2)
        return next(currency for currency in repository.list_all() if currency.name == name)

    def create_category(self, name: str = "Food") -> Category:
        repository = SqliteCategoryRepository(self.connection)
        repository.create(name, None)
        return next(category for category in repository.list_all() if category.name == name)

    def create_account(self, name: str = "Checking", currency: Currency | None = None) -> Account:
        selected_currency = currency or self.create_currency()
        repository = SqliteAccountRepository(self.connection)
        repository.create(name, None, selected_currency.uuid)
        return next(account for account in repository.list_all() if account.name == name)

    def create_tag(self, name: str = "Important") -> Tag:
        repository = SqliteTagRepository(self.connection)
        repository.create(name)
        return next(tag for tag in repository.list_all() if tag.name == name)

    def create_event(self, description: str = "Purchase", type: TransactionEventType = "TRANSACTION", occurred_at: int = 10) -> TransactionEvent:
        repository = SqliteTransactionEventRepository(self.connection)
        repository.create(occurred_at, description, type)
        return next(event for event in repository.list_all() if event.description == description)

    def create_budget(self, name: str = "Monthly", currency: Currency | None = None, category: Category | None = None) -> Budget:
        selected_currency = currency or self.create_currency()
        selected_category = category or self.create_category()
        repository = SqliteBudgetRepository(self.connection)
        repository.create(selected_category.uuid, selected_currency.uuid, 10, 20, name, "Monthly spending", 100)
        return next(budget for budget in repository.list_all() if budget.name == name)
