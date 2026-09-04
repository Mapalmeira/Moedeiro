from collections.abc import Callable
from uuid import UUID

from app.application.ledger.exceptions import AccountNotFoundError, CategoryNotFoundError, CurrencyNotFoundError, InvalidQueryParameterError, QueryPointLimitExceededError
from app.application.ledger.unit_of_work import LedgerUnitOfWork
from app.domain.ledger.model.cash_flow import CashFlow
from app.domain.ledger.model.financial_event_filter import FinancialEventFilter


def get_cash_flow_summary(unit_of_work_factory: Callable[[], LedgerUnitOfWork], currency_uuid: UUID, filters: FinancialEventFilter) -> CashFlow:
    with unit_of_work_factory() as unit_of_work:
        _require_filter_relations(unit_of_work, currency_uuid, filters)
        return unit_of_work.cash_flow_query_repository.get_summary(currency_uuid, filters)


def list_cash_flow_points(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    currency_uuid: UUID,
    filters: FinancialEventFilter,
    point_width: int,
    max_points: int,
) -> list[CashFlow]:
    if point_width < 1:
        raise InvalidQueryParameterError
    point_count = (filters.to_timestamp - filters.from_timestamp + point_width - 1) // point_width
    if point_count > max_points:
        raise QueryPointLimitExceededError
    with unit_of_work_factory() as unit_of_work:
        _require_filter_relations(unit_of_work, currency_uuid, filters)
        return unit_of_work.cash_flow_query_repository.list_points(currency_uuid, filters, point_width)


def _require_filter_relations(unit_of_work: LedgerUnitOfWork, currency_uuid: UUID, filters: FinancialEventFilter) -> None:
    if unit_of_work.currency_repository.get(currency_uuid) is None:
        raise CurrencyNotFoundError
    if filters.account_uuid is not None and unit_of_work.account_repository.get(filters.account_uuid) is None:
        raise AccountNotFoundError
    if filters.category_uuid is not None and unit_of_work.category_repository.get(filters.category_uuid) is None:
        raise CategoryNotFoundError
