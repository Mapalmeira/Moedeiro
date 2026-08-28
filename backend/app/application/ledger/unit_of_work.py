from abc import abstractmethod

from app.application.unit_of_work import UnitOfWork
from app.domain.ledger.repository.account import AccountRepository
from app.domain.ledger.repository.budget import BudgetRepository
from app.domain.ledger.repository.category import CategoryRepository
from app.domain.ledger.repository.currency import CurrencyRepository
from app.domain.ledger.repository.financial_movement import FinancialMovementRepository
from app.domain.ledger.repository.ledger_metadata import LedgerMetadataRepository
from app.domain.ledger.repository.tag import TagRepository
from app.domain.ledger.repository.transaction_event import TransactionEventRepository


class LedgerUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def account_repository(self) -> AccountRepository:
        pass

    @property
    @abstractmethod
    def budget_repository(self) -> BudgetRepository:
        pass

    @property
    @abstractmethod
    def category_repository(self) -> CategoryRepository:
        pass

    @property
    @abstractmethod
    def currency_repository(self) -> CurrencyRepository:
        pass

    @property
    @abstractmethod
    def financial_movement_repository(self) -> FinancialMovementRepository:
        pass

    @property
    @abstractmethod
    def ledger_metadata_repository(self) -> LedgerMetadataRepository:
        pass

    @property
    @abstractmethod
    def tag_repository(self) -> TagRepository:
        pass

    @property
    @abstractmethod
    def transaction_event_repository(self) -> TransactionEventRepository:
        pass
