from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from app.api.dependencies.authentication import AuthenticatedUser
from app.api.dependencies.ledger import ledger_unit_of_work_factory
from app.api.ledger.schema.account import AccountResponse, CreateAccountRequest, UpdateAccountRequest
from app.application.ledger.exceptions import AccountInUseError, AccountLimitReachedError, AccountNameUnavailableError, AccountNotFoundError, CurrencyNotFoundError
from app.application.ledger.use_cases.account import create_account, delete_account, get_account, list_accounts, update_account


router = APIRouter(prefix="/api/ledgers/{ledger_uuid}/accounts", tags=["accounts"])


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_ledger_account(ledger_uuid: UUID, payload: CreateAccountRequest, request: Request, user: AuthenticatedUser) -> AccountResponse:
    try:
        account = create_account(
            ledger_unit_of_work_factory(request, user.uuid, ledger_uuid),
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
    except AccountLimitReachedError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account limit reached") from error
    return AccountResponse.from_account(account)


@router.get("", response_model=list[AccountResponse])
def list_ledger_accounts(
    ledger_uuid: UUID,
    request: Request,
    user: AuthenticatedUser,
) -> list[AccountResponse]:
    accounts = list_accounts(ledger_unit_of_work_factory(request, user.uuid, ledger_uuid))
    return [AccountResponse.from_account(account) for account in accounts]


@router.get("/{account_uuid}", response_model=AccountResponse)
def get_ledger_account(ledger_uuid: UUID, account_uuid: UUID, request: Request, user: AuthenticatedUser) -> AccountResponse:
    try:
        account = get_account(ledger_unit_of_work_factory(request, user.uuid, ledger_uuid), account_uuid)
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
            ledger_unit_of_work_factory(request, user.uuid, ledger_uuid),
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
        delete_account(ledger_unit_of_work_factory(request, user.uuid, ledger_uuid), account_uuid)
    except AccountNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found") from error
    except AccountInUseError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account is in use") from error
