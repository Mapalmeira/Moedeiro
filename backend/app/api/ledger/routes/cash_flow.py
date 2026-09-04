from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.api.dependencies.authentication import AuthenticatedUser
from app.api.dependencies.ledger import ledger_unit_of_work_factory
from app.api.ledger.schema.cash_flow import CashFlowResponse
from app.application.ledger.exceptions import AccountNotFoundError, CategoryNotFoundError, CurrencyNotFoundError
from app.application.ledger.use_cases.cash_flow import get_cash_flow_summary, list_cash_flow_points
from app.domain.ledger.model.financial_event import FinancialEventType
from app.domain.ledger.model.financial_event_filter import FinancialEventFilter


router = APIRouter(prefix="/api/ledgers/{ledger_uuid}/cash-flow", tags=["cash flow"])


@router.get("", response_model=CashFlowResponse)
def get_ledger_cash_flow(
    ledger_uuid: UUID,
    currency_uuid: UUID,
    from_timestamp: int,
    to_timestamp: int,
    request: Request,
    user: AuthenticatedUser,
    account_uuid: UUID | None = None,
    category_uuid: UUID | None = None,
    event_type: FinancialEventType | None = None,
) -> CashFlowResponse:
    try:
        filters = _filters(from_timestamp, to_timestamp, account_uuid, category_uuid, event_type)
        cash_flow = get_cash_flow_summary(ledger_unit_of_work_factory(request, user.uuid, ledger_uuid), currency_uuid, filters)
    except CurrencyNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency not found") from error
    except AccountNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found") from error
    except CategoryNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found") from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return CashFlowResponse.from_cash_flow(cash_flow)


@router.get("/points", response_model=list[CashFlowResponse])
def list_ledger_cash_flow_points(
    ledger_uuid: UUID,
    currency_uuid: UUID,
    from_timestamp: int,
    to_timestamp: int,
    point_width: Annotated[int, Query(ge=1)],
    request: Request,
    user: AuthenticatedUser,
    account_uuid: UUID | None = None,
    category_uuid: UUID | None = None,
    event_type: FinancialEventType | None = None,
) -> list[CashFlowResponse]:
    try:
        filters = _filters(from_timestamp, to_timestamp, account_uuid, category_uuid, event_type)
        points = list_cash_flow_points(
            ledger_unit_of_work_factory(request, user.uuid, ledger_uuid),
            currency_uuid,
            filters,
            point_width,
            request.app.state.settings.max_query_points,
        )
    except CurrencyNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency not found") from error
    except AccountNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found") from error
    except CategoryNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found") from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return [CashFlowResponse.from_cash_flow(point) for point in points]


def _filters(from_timestamp: int, to_timestamp: int, account_uuid: UUID | None, category_uuid: UUID | None, event_type: FinancialEventType | None) -> FinancialEventFilter:
    return FinancialEventFilter(from_timestamp=from_timestamp, to_timestamp=to_timestamp, account_uuid=account_uuid, category_uuid=category_uuid, event_type=event_type)
