import time
from collections.abc import Callable
from functools import partial
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.api.authentication import AuthenticatedUser
from app.api.schema.currency import CreateCurrencyRequest, CurrencyResponse, CurrencySortKey, UpdateCurrencyRequest
from app.application.ledger.exceptions import CurrencyInUseError, CurrencyNotFoundError, LedgerNotFoundError
from app.application.ledger.unit_of_work import LedgerUnitOfWork
from app.application.ledger.use_cases.currency import create_currency, delete_currency, get_currency, list_currency_page, update_currency
from app.application.ledger.use_cases.ledger import access_owned_ledger


router = APIRouter(prefix="/api/ledgers/{ledger_uuid}/currencies", tags=["currencies"])


@router.post("", response_model=CurrencyResponse, status_code=status.HTTP_201_CREATED)
def create_ledger_currency(
    ledger_uuid: UUID,
    payload: CreateCurrencyRequest,
    request: Request,
    user: AuthenticatedUser,
) -> CurrencyResponse:
    currency = create_currency(
        _unit_of_work_factory(request, user.uuid, ledger_uuid),
        payload.name,
        payload.prefix,
        payload.suffix,
        payload.decimal_places,
        payload.icon,
        bytes.fromhex(payload.color_code[1:]),
    )
    return CurrencyResponse.from_currency(currency)


@router.get("", response_model=list[CurrencyResponse])
def list_ledger_currencies(
    ledger_uuid: UUID,
    request: Request,
    user: AuthenticatedUser,
    page_number: Annotated[int, Query(ge=1)],
    page_size: Annotated[int, Query(ge=1, le=200)],
    sort_key: CurrencySortKey = "name",
    ascending: bool = True,
) -> list[CurrencyResponse]:
    currencies = list_currency_page(
        _unit_of_work_factory(request, user.uuid, ledger_uuid),
        page_number,
        page_size,
        sort_key,
        ascending,
    )
    return [CurrencyResponse.from_currency(currency) for currency in currencies]


@router.get("/{currency_uuid}", response_model=CurrencyResponse)
def get_ledger_currency(
    ledger_uuid: UUID,
    currency_uuid: UUID,
    request: Request,
    user: AuthenticatedUser,
) -> CurrencyResponse:
    try:
        currency = get_currency(
            _unit_of_work_factory(request, user.uuid, ledger_uuid),
            currency_uuid,
        )
    except CurrencyNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency not found") from error
    return CurrencyResponse.from_currency(currency)


@router.put("/{currency_uuid}", response_model=CurrencyResponse)
def update_ledger_currency(
    ledger_uuid: UUID,
    currency_uuid: UUID,
    payload: UpdateCurrencyRequest,
    request: Request,
    user: AuthenticatedUser,
) -> CurrencyResponse:
    try:
        currency = update_currency(
            _unit_of_work_factory(request, user.uuid, ledger_uuid),
            currency_uuid,
            payload.name,
            payload.prefix,
            payload.suffix,
            payload.icon,
            bytes.fromhex(payload.color_code[1:]),
        )
    except CurrencyNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency not found") from error
    return CurrencyResponse.from_currency(currency)


@router.delete("/{currency_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ledger_currency(
    ledger_uuid: UUID,
    currency_uuid: UUID,
    request: Request,
    user: AuthenticatedUser,
) -> None:
    try:
        delete_currency(
            _unit_of_work_factory(request, user.uuid, ledger_uuid),
            currency_uuid,
        )
    except CurrencyNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency not found") from error
    except CurrencyInUseError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Currency is in use") from error


def _unit_of_work_factory(
    request: Request,
    user_uuid: UUID,
    ledger_uuid: UUID,
) -> Callable[[], LedgerUnitOfWork]:
    try:
        ledger = access_owned_ledger(
            request.app.state.databases.open_registry,
            user_uuid,
            ledger_uuid,
            int(time.time()),
        )
    except LedgerNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ledger not found") from error
    return partial(request.app.state.databases.open_ledger, ledger.path)
