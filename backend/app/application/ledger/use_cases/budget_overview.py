from collections.abc import Callable, Collection
from uuid import UUID

from app.application.ledger.exceptions import AccountNotFoundError, CategoryNotFoundError, CurrencyNotFoundError
from app.application.ledger.unit_of_work import LedgerUnitOfWork
from app.domain.ledger.model.budget_overview import BudgetOverviewItem, BudgetOverviewState


_ALL_STATES: tuple[BudgetOverviewState, ...] = ("FUTURE", "ACTIVE", "FINISHED")


def list_budget_overview(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    timestamp: int,
    states: Collection[BudgetOverviewState],
    account_uuid: UUID | None,
    category_uuid: UUID | None,
    search: str | None,
    page_size: int,
    cursor_name: str | None,
    cursor_uuid: UUID | None,
) -> list[BudgetOverviewItem]:
    selected_states = tuple(dict.fromkeys(states)) or _ALL_STATES
    with unit_of_work_factory() as unit_of_work:
        if account_uuid is not None and unit_of_work.account_repository.get(account_uuid) is None:
            raise AccountNotFoundError
        if category_uuid is not None and unit_of_work.category_repository.get(category_uuid) is None:
            raise CategoryNotFoundError
        return unit_of_work.budget_overview_query_repository.list_page(
            timestamp,
            selected_states,
            account_uuid,
            category_uuid,
            search,
            page_size,
            cursor_name,
            cursor_uuid,
        )


def list_budgets_for_currency(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    timestamp: int,
    currency_uuid: UUID,
    limit: int,
) -> list[BudgetOverviewItem]:
    with unit_of_work_factory() as unit_of_work:
        if unit_of_work.currency_repository.get(currency_uuid) is None:
            raise CurrencyNotFoundError
        return unit_of_work.budget_overview_query_repository.list_for_currency(timestamp, currency_uuid, limit)
