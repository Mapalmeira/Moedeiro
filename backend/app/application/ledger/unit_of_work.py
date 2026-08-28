"""Transactional wrapper exposing repositories for one ledger operation."""

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
    account_repository: AccountRepository
    budget_repository: BudgetRepository
    category_repository: CategoryRepository
    currency_repository: CurrencyRepository
    financial_movement_repository: FinancialMovementRepository
    ledger_metadata_repository: LedgerMetadataRepository
    tag_repository: TagRepository
    transaction_event_repository: TransactionEventRepository
