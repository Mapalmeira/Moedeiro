from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.api.dependencies.authentication import AuthenticatedUser
from app.api.dependencies.ledger import ledger_unit_of_work_factory
from app.api.dependencies.pagination import validate_page_size
from app.api.ledger.schema.financial_event import AccountTransferFinancialEventRequest, CreateFinancialEventRequest, FinancialEventPageResponse, FinancialEventResponse, ShoppingListFinancialEventRequest, SimpleFinancialEventRequest, UpdateAccountTransferFinancialEventRequest, UpdateFinancialEventRequest, UpdateShoppingListFinancialEventRequest, UpdateSimpleFinancialEventRequest
from app.application.ledger.exceptions import AccountNotFoundError, CategoryNotFoundError, FinancialEventNotFoundError, FinancialEventTypeMismatchError, FinancialMovementNotFoundError, InvalidFinancialEventError, InvalidFinancialEventStructureError
from app.application.ledger.use_cases.financial_event import create_account_transfer_financial_event, create_shopping_list_financial_event, create_simple_financial_event, delete_financial_event, get_financial_event, list_financial_events_after, update_account_transfer_financial_event, update_shopping_list_financial_event, update_simple_financial_event
from app.domain.ledger.model.financial_event import FinancialEventType
from app.domain.ledger.model.financial_event_filter import FinancialEventFilter


router = APIRouter(prefix="/api/ledgers/{ledger_uuid}/events", tags=["financial events"])


@router.post("", response_model=FinancialEventResponse, status_code=status.HTTP_201_CREATED)
def create_ledger_financial_event(ledger_uuid: UUID, payload: CreateFinancialEventRequest, request: Request, user: AuthenticatedUser) -> FinancialEventResponse:
    unit_of_work_factory = ledger_unit_of_work_factory(request, user.uuid, ledger_uuid)
    try:
        if isinstance(payload, SimpleFinancialEventRequest):
            event = create_simple_financial_event(unit_of_work_factory, payload.occurred_at, payload.description, payload.account_uuid, payload.category_uuid, payload.value, payload.quantity, payload.item_name)
        elif isinstance(payload, ShoppingListFinancialEventRequest):
            event = create_shopping_list_financial_event(
                unit_of_work_factory,
                payload.occurred_at,
                payload.description,
                payload.account_uuid,
                [(movement.category_uuid, movement.value, movement.quantity, movement.item_name) for movement in payload.movements],
            )
        elif isinstance(payload, AccountTransferFinancialEventRequest):
            fee = None if payload.fee is None else (payload.fee.category_uuid, payload.fee.value)
            event = create_account_transfer_financial_event(
                unit_of_work_factory,
                payload.occurred_at,
                payload.description,
                payload.source_account_uuid,
                payload.source_category_uuid,
                payload.source_value,
                payload.destination_account_uuid,
                payload.destination_category_uuid,
                payload.destination_value,
                fee,
            )
        else:
            raise TypeError("unsupported financial event request")
    except AccountNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found") from error
    except CategoryNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found") from error
    except InvalidFinancialEventError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid financial event") from error
    return FinancialEventResponse.from_event(event)


@router.get("", response_model=FinancialEventPageResponse)
def list_ledger_financial_events(
    ledger_uuid: UUID,
    request: Request,
    user: AuthenticatedUser,
    from_timestamp: int,
    to_timestamp: int,
    page_size: Annotated[int, Query(ge=1)],
    account_uuid: UUID | None = None,
    category_uuid: UUID | None = None,
    event_type: FinancialEventType | None = None,
    ascending: bool = False,
    cursor: Annotated[str | None, Query(max_length=53)] = None,
) -> FinancialEventPageResponse:
    validate_page_size(request, page_size)
    if from_timestamp >= to_timestamp:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="from_timestamp must be less than to_timestamp")
    filters = FinancialEventFilter(
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
        account_uuid=account_uuid,
        category_uuid=category_uuid,
        event_type=event_type,
    )
    try:
        cursor_occurred_at, cursor_uuid = _parse_cursor(cursor)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid cursor") from error
    events = list_financial_events_after(
        ledger_unit_of_work_factory(request, user.uuid, ledger_uuid), page_size, ascending, filters, cursor_occurred_at, cursor_uuid
    )
    next_cursor = None
    if len(events) > page_size:
        events = events[:page_size]
        next_cursor = _format_cursor(events[-1])
    return FinancialEventPageResponse(events=[FinancialEventResponse.from_event(event) for event in events], next_cursor=next_cursor)


def _format_cursor(event) -> str:
    return f"{event.occurred_at}:{event.uuid.hex}"


def _parse_cursor(cursor: str | None) -> tuple[int | None, UUID | None]:
    if cursor is None:
        return None, None
    occurred_at, raw_uuid = cursor.split(":")
    return int(occurred_at), UUID(hex=raw_uuid)


@router.get("/{event_uuid}", response_model=FinancialEventResponse)
def get_ledger_financial_event(ledger_uuid: UUID, event_uuid: UUID, request: Request, user: AuthenticatedUser) -> FinancialEventResponse:
    try:
        event = get_financial_event(ledger_unit_of_work_factory(request, user.uuid, ledger_uuid), event_uuid)
    except FinancialEventNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Financial event not found") from error
    return FinancialEventResponse.from_event(event)


@router.put("/{event_uuid}", response_model=FinancialEventResponse)
def update_ledger_financial_event(ledger_uuid: UUID, event_uuid: UUID, payload: UpdateFinancialEventRequest, request: Request, user: AuthenticatedUser) -> FinancialEventResponse:
    unit_of_work_factory = ledger_unit_of_work_factory(request, user.uuid, ledger_uuid)
    try:
        if isinstance(payload, UpdateSimpleFinancialEventRequest):
            event = update_simple_financial_event(unit_of_work_factory, event_uuid, payload.occurred_at, payload.description, payload.account_uuid, payload.category_uuid, payload.value, payload.quantity, payload.item_name)
        elif isinstance(payload, UpdateShoppingListFinancialEventRequest):
            event = update_shopping_list_financial_event(
                unit_of_work_factory,
                event_uuid,
                payload.occurred_at,
                payload.description,
                payload.account_uuid,
                [(movement.uuid, movement.category_uuid, movement.value, movement.quantity, movement.item_name) for movement in payload.movements],
            )
        elif isinstance(payload, UpdateAccountTransferFinancialEventRequest):
            fee = None if payload.fee is None else (payload.fee.category_uuid, payload.fee.value)
            event = update_account_transfer_financial_event(
                unit_of_work_factory,
                event_uuid,
                payload.occurred_at,
                payload.description,
                payload.source_account_uuid,
                payload.source_category_uuid,
                payload.source_value,
                payload.destination_account_uuid,
                payload.destination_category_uuid,
                payload.destination_value,
                fee,
            )
        else:
            raise TypeError("unsupported financial event request")
    except FinancialEventNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Financial event not found") from error
    except FinancialMovementNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Financial movement not found") from error
    except AccountNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found") from error
    except CategoryNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found") from error
    except FinancialEventTypeMismatchError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Financial event type cannot be changed") from error
    except InvalidFinancialEventStructureError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stored financial event structure is invalid") from error
    except InvalidFinancialEventError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid financial event") from error
    return FinancialEventResponse.from_event(event)


@router.delete("/{event_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ledger_financial_event(ledger_uuid: UUID, event_uuid: UUID, request: Request, user: AuthenticatedUser) -> None:
    try:
        delete_financial_event(ledger_unit_of_work_factory(request, user.uuid, ledger_uuid), event_uuid)
    except FinancialEventNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Financial event not found") from error
