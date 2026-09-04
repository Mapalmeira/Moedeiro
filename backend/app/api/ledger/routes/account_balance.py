from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.api.dependencies.authentication import AuthenticatedUser
from app.api.dependencies.ledger import ledger_unit_of_work_factory
from app.application.ledger.exceptions import AccountNotFoundError, QueryPointLimitExceededError
from app.application.ledger.use_cases.account_balance import get_account_balance, list_account_balance_points


router = APIRouter(prefix="/api/ledgers/{ledger_uuid}/accounts/{account_uuid}/balance", tags=["account balance"])


@router.get("", response_model=int)
def get_ledger_account_balance(ledger_uuid: UUID, account_uuid: UUID, timestamp: int, request: Request, user: AuthenticatedUser) -> int:
    try:
        return get_account_balance(ledger_unit_of_work_factory(request, user.uuid, ledger_uuid), account_uuid, timestamp)
    except AccountNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found") from error


@router.get("/points", response_model=list[int])
def list_ledger_account_balance_points(
    ledger_uuid: UUID,
    account_uuid: UUID,
    request: Request,
    user: AuthenticatedUser,
    from_timestamp: int,
    point_count: Annotated[int, Query(ge=1)],
    point_interval: Annotated[int, Query(ge=1)],
) -> list[int]:
    try:
        return list_account_balance_points(
            ledger_unit_of_work_factory(request, user.uuid, ledger_uuid),
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
