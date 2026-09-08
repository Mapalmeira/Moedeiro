import base64
import time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.api.dependencies.authentication import AuthenticatedUser
from app.api.dependencies.ledger import ledger_unit_of_work_factory
from app.api.dependencies.pagination import validate_page_size
from app.api.ledger.schema.budget import BudgetOverviewPageResponse, BudgetOverviewResponse, BudgetResponse, CreateBudgetRequest, UpdateBudgetRequest
from app.application.ledger.exceptions import AccountNotFoundError, BudgetLimitReachedError, BudgetNameUnavailableError, BudgetNotFoundError, CategoryNotFoundError
from app.application.ledger.use_cases.budget import create_budget, delete_budget, get_budget, update_budget
from app.application.ledger.use_cases.budget_overview import list_budget_attention, list_budget_overview
from app.domain.ledger.model.budget import Budget
from app.domain.ledger.model.budget_overview import BudgetOverviewState


router = APIRouter(prefix="/api/ledgers/{ledger_uuid}/budgets", tags=["budgets"])


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_ledger_budget(ledger_uuid: UUID, payload: CreateBudgetRequest, request: Request, user: AuthenticatedUser) -> BudgetResponse:
    try:
        budget = create_budget(
            ledger_unit_of_work_factory(request, user.uuid, ledger_uuid),
            payload.account_uuid,
            payload.category_uuid,
            payload.from_timestamp,
            payload.to_timestamp,
            payload.name,
            payload.description,
            payload.amount,
        )
    except AccountNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found") from error
    except CategoryNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found") from error
    except BudgetNameUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Budget name unavailable") from error
    except BudgetLimitReachedError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Budget limit reached") from error
    return BudgetResponse.from_budget(budget)


@router.get("/overview", response_model=BudgetOverviewPageResponse)
def list_ledger_budget_overview(
    ledger_uuid: UUID,
    request: Request,
    user: AuthenticatedUser,
    page_size: Annotated[int, Query(ge=1)],
    state: Annotated[list[BudgetOverviewState] | None, Query()] = None,
    account_uuid: UUID | None = None,
    search: Annotated[str | None, Query(max_length=50)] = None,
    cursor: Annotated[str | None, Query(max_length=160)] = None,
) -> BudgetOverviewPageResponse:
    validate_page_size(request, page_size)
    try:
        cursor_name, cursor_uuid = _parse_cursor(cursor)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid cursor") from error
    try:
        items = list_budget_overview(
            ledger_unit_of_work_factory(request, user.uuid, ledger_uuid),
            int(time.time()),
            state or ("FUTURE", "ACTIVE", "FINISHED"),
            account_uuid,
            search.strip() if search and search.strip() else None,
            page_size + 1,
            cursor_name,
            cursor_uuid,
        )
    except AccountNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found") from error
    next_cursor = None
    if len(items) > page_size:
        items = items[:page_size]
        next_cursor = _format_cursor(items[-1].budget)
    return BudgetOverviewPageResponse(items=[BudgetOverviewResponse.from_overview(item) for item in items], next_cursor=next_cursor)


@router.get("/attention", response_model=list[BudgetOverviewResponse])
def list_ledger_budget_attention(
    ledger_uuid: UUID,
    account_uuid: UUID,
    request: Request,
    user: AuthenticatedUser,
    limit: Annotated[int, Query(ge=1)] = 3,
) -> list[BudgetOverviewResponse]:
    validate_page_size(request, limit)
    try:
        items = list_budget_attention(
            ledger_unit_of_work_factory(request, user.uuid, ledger_uuid),
            int(time.time()),
            account_uuid,
            limit,
        )
    except AccountNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found") from error
    return [BudgetOverviewResponse.from_overview(item) for item in items]


@router.get("/{budget_uuid}", response_model=BudgetResponse)
def get_ledger_budget(ledger_uuid: UUID, budget_uuid: UUID, request: Request, user: AuthenticatedUser) -> BudgetResponse:
    try:
        budget = get_budget(ledger_unit_of_work_factory(request, user.uuid, ledger_uuid), budget_uuid)
    except BudgetNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found") from error
    return BudgetResponse.from_budget(budget)


@router.put("/{budget_uuid}", response_model=BudgetResponse)
def update_ledger_budget(ledger_uuid: UUID, budget_uuid: UUID, payload: UpdateBudgetRequest, request: Request, user: AuthenticatedUser) -> BudgetResponse:
    try:
        budget = update_budget(
            ledger_unit_of_work_factory(request, user.uuid, ledger_uuid),
            budget_uuid,
            payload.category_uuid,
            payload.from_timestamp,
            payload.to_timestamp,
            payload.name,
            payload.description,
            payload.amount,
        )
    except BudgetNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found") from error
    except CategoryNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found") from error
    except BudgetNameUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Budget name unavailable") from error
    return BudgetResponse.from_budget(budget)


@router.delete("/{budget_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ledger_budget(ledger_uuid: UUID, budget_uuid: UUID, request: Request, user: AuthenticatedUser) -> None:
    try:
        delete_budget(ledger_unit_of_work_factory(request, user.uuid, ledger_uuid), budget_uuid)
    except BudgetNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found") from error


def _format_cursor(budget: Budget) -> str:
    raw = f"{budget.uuid.hex}:{budget.name}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _parse_cursor(cursor: str | None) -> tuple[str | None, UUID | None]:
    if cursor is None:
        return None, None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        raw_uuid, name = raw.split(":", 1)
        if not name:
            raise ValueError
        return name, UUID(hex=raw_uuid)
    except (UnicodeError, ValueError) as error:
        raise ValueError("invalid budget cursor") from error
