from collections.abc import Callable
from uuid import UUID

from app.application.ledger.exceptions import BudgetNotActiveError, BudgetNotFoundError
from app.application.ledger.unit_of_work import LedgerUnitOfWork
from app.domain.ledger.model.budget_status import BudgetStatus


def get_budget_status(unit_of_work_factory: Callable[[], LedgerUnitOfWork], budget_uuid: UUID, timestamp: int) -> BudgetStatus:
    with unit_of_work_factory() as unit_of_work:
        if unit_of_work.budget_repository.get(budget_uuid) is None:
            raise BudgetNotFoundError
        budget_status = unit_of_work.budget_status_query_repository.get_status(budget_uuid, timestamp)
        if budget_status is None:
            raise BudgetNotActiveError
        return budget_status


def list_budget_status_page(unit_of_work_factory: Callable[[], LedgerUnitOfWork], timestamp: int, page_number: int, page_size: int) -> list[BudgetStatus]:
    with unit_of_work_factory() as unit_of_work:
        return unit_of_work.budget_status_query_repository.list_page(timestamp, page_number, page_size)
