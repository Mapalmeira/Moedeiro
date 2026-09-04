from collections.abc import Callable
from uuid import UUID

from app.application.ledger.exceptions import AccountNotFoundError
from app.application.ledger.unit_of_work import LedgerUnitOfWork


def get_account_balance(unit_of_work_factory: Callable[[], LedgerUnitOfWork], account_uuid: UUID, timestamp: int) -> int:
    with unit_of_work_factory() as unit_of_work:
        try:
            return unit_of_work.account_balance_query_repository.get_balance_at(account_uuid, timestamp)
        except LookupError as error:
            raise AccountNotFoundError from error


def list_account_balance_points(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    account_uuid: UUID,
    from_timestamp: int,
    point_count: int,
    point_interval: int,
    max_points: int,
) -> list[int]:
    if point_count > max_points:
        raise ValueError(f"point_count must be less than or equal to {max_points}")
    with unit_of_work_factory() as unit_of_work:
        try:
            return unit_of_work.account_balance_query_repository.list_points(account_uuid, from_timestamp, point_count, point_interval)
        except LookupError as error:
            raise AccountNotFoundError from error
