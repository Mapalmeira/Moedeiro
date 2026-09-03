from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.api.dependencies.authentication import AuthenticatedUser
from app.api.dependencies.ledger import ledger_unit_of_work_factory
from app.api.dependencies.pagination import validate_requested_page
from app.api.ledger.schema.currency import CreateCurrencyRequest, CurrencyResponse, CurrencySortKey, UpdateCurrencyRequest
from app.application.ledger.exceptions import CurrencyInUseError, CurrencyNotFoundError
from app.application.ledger.use_cases.currency import create_currency, delete_currency, get_currency, list_currency_page, update_currency


router = APIRouter(prefix="/api/ledgers/{ledger_uuid}/currencies", tags=["currencies"])


@router.post("", response_model=CurrencyResponse, status_code=status.HTTP_201_CREATED)
def create_ledger_currency(
    ledger_uuid: UUID,
    payload: CreateCurrencyRequest,
    request: Request,
    user: AuthenticatedUser,
) -> CurrencyResponse:
    currency = create_currency(
        ledger_unit_of_work_factory(request, user.uuid, ledger_uuid),
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
    page_size: Annotated[int, Query(ge=1)],
    sort_key: CurrencySortKey = "name",
    ascending: bool = True,
) -> list[CurrencyResponse]:
    validate_requested_page(request, page_number, page_size)
    currencies = list_currency_page(
        ledger_unit_of_work_factory(request, user.uuid, ledger_uuid),
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
            ledger_unit_of_work_factory(request, user.uuid, ledger_uuid),
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
            ledger_unit_of_work_factory(request, user.uuid, ledger_uuid),
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
            ledger_unit_of_work_factory(request, user.uuid, ledger_uuid),
            currency_uuid,
        )
    except CurrencyNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency not found") from error
    except CurrencyInUseError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Currency is in use") from error
