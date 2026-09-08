"""Transactional wrapper exposing repositories for one ledger operation."""

from app.application.unit_of_work import UnitOfWork
from app.domain.ledger.repository.account import AccountRepository
from app.domain.ledger.repository.account_balance_query import AccountBalanceQueryRepository
from app.domain.ledger.repository.budget import BudgetRepository
from app.domain.ledger.repository.budget_overview_query import BudgetOverviewQueryRepository
from app.domain.ledger.repository.cash_flow_query import CashFlowQueryRepository
from app.domain.ledger.repository.category import CategoryRepository
from app.domain.ledger.repository.currency import CurrencyRepository
from app.domain.ledger.repository.financial_event import FinancialEventRepository
from app.domain.ledger.repository.financial_movement import FinancialMovementRepository
from app.domain.ledger.repository.ledger_metadata import LedgerMetadataRepository


class LedgerUnitOfWork(UnitOfWork):
    account_repository: AccountRepository
    account_balance_query_repository: AccountBalanceQueryRepository
    budget_repository: BudgetRepository
    budget_overview_query_repository: BudgetOverviewQueryRepository
    cash_flow_query_repository: CashFlowQueryRepository
    category_repository: CategoryRepository
    currency_repository: CurrencyRepository
    financial_movement_repository: FinancialMovementRepository
    ledger_metadata_repository: LedgerMetadataRepository
    financial_event_repository: FinancialEventRepository
