from typing import Self
from uuid import UUID

from pydantic import BaseModel

from app.domain.ledger.model.cash_flow import CashFlow


class CashFlowResponse(BaseModel):
    currency_uuid: UUID
    income: int
    expense: int
    event_count: int
    income_movement_count: int
    expense_movement_count: int

    @classmethod
    def from_cash_flow(cls, cash_flow: CashFlow) -> Self:
        return cls.model_validate(cash_flow.model_dump())
