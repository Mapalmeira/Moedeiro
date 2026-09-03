import time
from collections.abc import Callable
from functools import partial
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.api.authentication import AuthenticatedUser
from app.api.schema.account import AccountResponse, AccountSortKey, CreateAccountRequest, UpdateAccountRequest
from app.application.ledger.exceptions import AccountInUseError, AccountNameUnavailableError, AccountNotFoundError, CurrencyNotFoundError, LedgerNotFoundError
from app.application.ledger.unit_of_work import LedgerUnitOfWork
from app.application.ledger.use_cases.account import create_account, delete_account, get_account, list_account_page, update_account
from app.application.ledger.use_cases.ledger import access_owned_ledger


router = APIRouter(prefix="/api/ledgers/{ledger_uuid}/accounts", tags=["accounts"])


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_ledger_account(ledger_uuid: UUID, payload: CreateAccountRequest, request: Request, user: AuthenticatedUser) -> AccountResponse:
    try:
        account = create_account(
            _unit_of_work_factory(request, user.uuid, ledger_uuid),
            payload.name,
            payload.note,
            payload.currency_uuid,
            payload.icon,
            bytes.fromhex(payload.color_code[1:]),
        )
    except CurrencyNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency not found") from error
    except AccountNameUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account name unavailable") from error
    return AccountResponse.from_account(account)


@router.get("", response_model=list[AccountResponse])
def list_ledger_accounts(
    ledger_uuid: UUID,
    request: Request,
    user: AuthenticatedUser,
    page_number: Annotated[int, Query(ge=1)],
    page_size: Annotated[int, Query(ge=1, le=200)],
    sort_key: AccountSortKey = "name",
    ascending: bool = True,
) -> list[AccountResponse]:
    accounts = list_account_page(_unit_of_work_factory(request, user.uuid, ledger_uuid), page_number, page_size, sort_key, ascending)
    return [AccountResponse.from_account(account) for account in accounts]


@router.get("/{account_uuid}", response_model=AccountResponse)
def get_ledger_account(ledger_uuid: UUID, account_uuid: UUID, request: Request, user: AuthenticatedUser) -> AccountResponse:
    try:
        account = get_account(_unit_of_work_factory(request, user.uuid, ledger_uuid), account_uuid)
    except AccountNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found") from error
    return AccountResponse.from_account(account)


@router.put("/{account_uuid}", response_model=AccountResponse)
def update_ledger_account(
    ledger_uuid: UUID,
    account_uuid: UUID,
    payload: UpdateAccountRequest,
    request: Request,
    user: AuthenticatedUser,
) -> AccountResponse:
    try:
        account = update_account(
            _unit_of_work_factory(request, user.uuid, ledger_uuid),
            account_uuid,
            payload.name,
            payload.note,
            payload.icon,
            bytes.fromhex(payload.color_code[1:]),
        )
    except AccountNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found") from error
    except AccountNameUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account name unavailable") from error
    return AccountResponse.from_account(account)


@router.delete("/{account_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ledger_account(ledger_uuid: UUID, account_uuid: UUID, request: Request, user: AuthenticatedUser) -> None:
    try:
        delete_account(_unit_of_work_factory(request, user.uuid, ledger_uuid), account_uuid)
    except AccountNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found") from error
    except AccountInUseError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account is in use") from error


def _unit_of_work_factory(request: Request, user_uuid: UUID, ledger_uuid: UUID) -> Callable[[], LedgerUnitOfWork]:
    try:
        ledger = access_owned_ledger(request.app.state.databases.open_registry, user_uuid, ledger_uuid, int(time.time()))
    except LedgerNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ledger not found") from error
    return partial(request.app.state.databases.open_ledger, ledger.path)
