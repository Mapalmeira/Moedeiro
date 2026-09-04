from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.api.dependencies.authentication import AuthenticatedUser
from app.api.dependencies.ledger import ledger_unit_of_work_factory
from app.api.dependencies.pagination import validate_requested_page
from app.api.ledger.schema.budget import BudgetResponse, BudgetSortKey, BudgetStatusResponse, CreateBudgetRequest, UpdateBudgetRequest
from app.application.ledger.exceptions import AccountNotFoundError, BudgetAccountCurrencyMismatchError, BudgetNameUnavailableError, BudgetNotActiveError, BudgetNotFoundError, CategoryNotFoundError, CurrencyNotFoundError
from app.application.ledger.use_cases.budget import create_budget, delete_budget, get_budget, list_budget_page, update_budget
from app.application.ledger.use_cases.budget_status import get_budget_status, list_budget_status_page


router = APIRouter(prefix="/api/ledgers/{ledger_uuid}/budgets", tags=["budgets"])


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_ledger_budget(ledger_uuid: UUID, payload: CreateBudgetRequest, request: Request, user: AuthenticatedUser) -> BudgetResponse:
    try:
        budget = create_budget(
            ledger_unit_of_work_factory(request, user.uuid, ledger_uuid),
            payload.category_uuid,
            payload.currency_uuid,
            payload.from_timestamp,
            payload.to_timestamp,
            payload.name,
            payload.description,
            payload.amount,
            payload.icon,
            bytes.fromhex(payload.color_code[1:]),
            payload.account_uuids,
        )
    except CurrencyNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency not found") from error
    except CategoryNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found") from error
    except AccountNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found") from error
    except BudgetNameUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Budget name unavailable") from error
    except BudgetAccountCurrencyMismatchError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Budget account uses a different currency") from error
    return BudgetResponse.from_budget(budget)


@router.get("", response_model=list[BudgetResponse])
def list_ledger_budgets(
    ledger_uuid: UUID,
    request: Request,
    user: AuthenticatedUser,
    page_number: Annotated[int, Query(ge=1)],
    page_size: Annotated[int, Query(ge=1)],
    sort_key: BudgetSortKey = "from_timestamp",
    ascending: bool = True,
) -> list[BudgetResponse]:
    validate_requested_page(request, page_number, page_size)
    budgets = list_budget_page(ledger_unit_of_work_factory(request, user.uuid, ledger_uuid), page_number, page_size, sort_key, ascending)
    return [BudgetResponse.from_budget(budget) for budget in budgets]


@router.get("/statuses", response_model=list[BudgetStatusResponse])
def list_ledger_budget_statuses(
    ledger_uuid: UUID,
    timestamp: int,
    request: Request,
    user: AuthenticatedUser,
    page_number: Annotated[int, Query(ge=1)],
    page_size: Annotated[int, Query(ge=1)],
) -> list[BudgetStatusResponse]:
    validate_requested_page(request, page_number, page_size)
    budget_statuses = list_budget_status_page(ledger_unit_of_work_factory(request, user.uuid, ledger_uuid), timestamp, page_number, page_size)
    return [BudgetStatusResponse.from_status(budget_status) for budget_status in budget_statuses]


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
            payload.icon,
            bytes.fromhex(payload.color_code[1:]),
            payload.account_uuids,
        )
    except BudgetNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found") from error
    except CategoryNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found") from error
    except AccountNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found") from error
    except BudgetNameUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Budget name unavailable") from error
    except BudgetAccountCurrencyMismatchError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Budget account uses a different currency") from error
    return BudgetResponse.from_budget(budget)


@router.delete("/{budget_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ledger_budget(ledger_uuid: UUID, budget_uuid: UUID, request: Request, user: AuthenticatedUser) -> None:
    try:
        delete_budget(ledger_unit_of_work_factory(request, user.uuid, ledger_uuid), budget_uuid)
    except BudgetNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found") from error


@router.get("/{budget_uuid}/status", response_model=BudgetStatusResponse)
def get_ledger_budget_status(ledger_uuid: UUID, budget_uuid: UUID, timestamp: int, request: Request, user: AuthenticatedUser) -> BudgetStatusResponse:
    try:
        budget_status = get_budget_status(ledger_unit_of_work_factory(request, user.uuid, ledger_uuid), budget_uuid, timestamp)
    except BudgetNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found") from error
    except BudgetNotActiveError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Budget is not active at timestamp") from error
    return BudgetStatusResponse.from_status(budget_status)
