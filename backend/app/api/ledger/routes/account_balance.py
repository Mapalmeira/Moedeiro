from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.api.dependencies.ledger import GrantedLedger, ledger_unit_of_work_factory
from app.api.dependencies.pagination import validate_page_size
from app.api.ledger.schema.account import AccountBalanceListResponse, AccountBalanceResponse
from app.application.ledger.exceptions import AccountNotFoundError, CurrencyNotFoundError, QueryPointLimitExceededError
from app.application.ledger.use_cases.account_balance import get_account_balance, list_account_balance_points, list_account_balances


router = APIRouter(prefix="/api/ledgers/{ledger_uuid}/accounts/{account_uuid}/balance", tags=["account balance"])
balances_router = APIRouter(prefix="/api/ledgers/{ledger_uuid}/balances", tags=["account balance"])


@balances_router.get("", response_model=AccountBalanceListResponse)
def list_ledger_account_balances(
    ledger_uuid: UUID,
    timestamp: int,
    request: Request,
    ledger: GrantedLedger,
    currency_uuid: UUID | None = None,
    limit: Annotated[int | None, Query(ge=1)] = None,
) -> AccountBalanceListResponse:
    if limit is not None:
        validate_page_size(request, limit)
    try:
        balances, total_balance = list_account_balances(
            ledger_unit_of_work_factory(request, ledger),
            timestamp,
            currency_uuid,
            limit,
        )
    except CurrencyNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency not found") from error
    return AccountBalanceListResponse(
        items=[
            AccountBalanceResponse(account_uuid=account_uuid, currency_uuid=balance_currency_uuid, balance=balance)
            for account_uuid, balance_currency_uuid, balance in balances
        ],
        total_balance=total_balance,
    )


@router.get("", response_model=int)
def get_ledger_account_balance(ledger_uuid: UUID, account_uuid: UUID, timestamp: int, request: Request, ledger: GrantedLedger) -> int:
    try:
        return get_account_balance(ledger_unit_of_work_factory(request, ledger), account_uuid, timestamp)
    except AccountNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found") from error


@router.get("/points", response_model=list[int])
def list_ledger_account_balance_points(
    ledger_uuid: UUID,
    account_uuid: UUID,
    request: Request,
    ledger: GrantedLedger,
    from_timestamp: int,
    point_count: Annotated[int, Query(ge=1)],
    point_interval: Annotated[int, Query(ge=1)],
) -> list[int]:
    try:
        return list_account_balance_points(
            ledger_unit_of_work_factory(request, ledger),
            account_uuid,
            from_timestamp,
            point_count,
            point_interval,
            request.app.state.settings.max_query_points,
        )
    except AccountNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found") from error
    except QueryPointLimitExceededError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Point count cannot exceed {request.app.state.settings.max_query_points}") from error
