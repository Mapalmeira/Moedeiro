from collections.abc import Callable
from uuid import UUID

from app.application.ledger.exceptions import AccountNotFoundError, CurrencyNotFoundError, QueryPointLimitExceededError
from app.application.ledger.unit_of_work import LedgerUnitOfWork


def get_account_balance(unit_of_work_factory: Callable[[], LedgerUnitOfWork], account_uuid: UUID, timestamp: int) -> int:
    with unit_of_work_factory() as unit_of_work:
        try:
            return unit_of_work.account_balance_query_repository.get_balance_at(account_uuid, timestamp)
        except LookupError as error:
            raise AccountNotFoundError from error


def list_account_balances(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    timestamp: int,
    currency_uuid: UUID | None = None,
    limit: int | None = None,
) -> tuple[list[tuple[UUID, UUID, int]], int | None]:
    with unit_of_work_factory() as unit_of_work:
        if currency_uuid is not None and unit_of_work.currency_repository.get(currency_uuid) is None:
            raise CurrencyNotFoundError
        balances = unit_of_work.account_balance_query_repository.list_balances_at(timestamp, currency_uuid, limit)
        total_balance = None if currency_uuid is None else unit_of_work.account_balance_query_repository.get_currency_balance_at(currency_uuid, timestamp)
        return balances, total_balance


def list_account_balance_points(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    account_uuid: UUID,
    from_timestamp: int,
    point_count: int,
    point_interval: int,
    max_points: int,
) -> list[int]:
    if point_count > max_points:
        raise QueryPointLimitExceededError
    with unit_of_work_factory() as unit_of_work:
        try:
            return unit_of_work.account_balance_query_repository.list_points(account_uuid, from_timestamp, point_count, point_interval)
        except LookupError as error:
            raise AccountNotFoundError from error
