from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from app.api.dependencies.ledger import GrantedLedger, ledger_unit_of_work_factory
from app.api.ledger.schema.currency import CreateCurrencyRequest, CurrencyResponse, UpdateCurrencyRequest
from app.application.ledger.exceptions import CurrencyInUseError, CurrencyLimitReachedError, CurrencyNameUnavailableError, CurrencyNotFoundError
from app.application.ledger.use_cases.currency import create_currency, delete_currency, get_currency, list_currencies, update_currency


router = APIRouter(prefix="/api/ledgers/{ledger_uuid}/currencies", tags=["currencies"])


@router.post("", response_model=CurrencyResponse, status_code=status.HTTP_201_CREATED)
def create_ledger_currency(
    ledger_uuid: UUID,
    payload: CreateCurrencyRequest,
    request: Request,
    ledger: GrantedLedger,
) -> CurrencyResponse:
    try:
        currency = create_currency(
            ledger_unit_of_work_factory(request, ledger),
            payload.name,
            payload.prefix,
            payload.suffix,
            payload.decimal_places,
            payload.icon,
            bytes.fromhex(payload.color_code[1:]),
        )
    except CurrencyLimitReachedError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Currency limit reached") from error
    except CurrencyNameUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Currency name unavailable") from error
    return CurrencyResponse.from_currency(currency)


@router.get("", response_model=list[CurrencyResponse])
def list_ledger_currencies(
    ledger_uuid: UUID,
    request: Request,
    ledger: GrantedLedger,
) -> list[CurrencyResponse]:
    currencies = list_currencies(ledger_unit_of_work_factory(request, ledger))
    return [CurrencyResponse.from_currency(currency) for currency in currencies]


@router.get("/{currency_uuid}", response_model=CurrencyResponse)
def get_ledger_currency(
    ledger_uuid: UUID,
    currency_uuid: UUID,
    request: Request,
    ledger: GrantedLedger,
) -> CurrencyResponse:
    try:
        currency = get_currency(
            ledger_unit_of_work_factory(request, ledger),
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
    ledger: GrantedLedger,
) -> CurrencyResponse:
    try:
        currency = update_currency(
            ledger_unit_of_work_factory(request, ledger),
            currency_uuid,
            payload.name,
            payload.prefix,
            payload.suffix,
            payload.icon,
            bytes.fromhex(payload.color_code[1:]),
        )
    except CurrencyNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency not found") from error
    except CurrencyNameUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Currency name unavailable") from error
    return CurrencyResponse.from_currency(currency)


@router.delete("/{currency_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ledger_currency(
    ledger_uuid: UUID,
    currency_uuid: UUID,
    request: Request,
    ledger: GrantedLedger,
) -> None:
    try:
        delete_currency(
            ledger_unit_of_work_factory(request, ledger),
            currency_uuid,
        )
    except CurrencyNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency not found") from error
    except CurrencyInUseError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Currency is in use") from error
