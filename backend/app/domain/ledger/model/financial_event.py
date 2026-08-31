from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from app.domain.ledger.model.financial_movement import FinancialMovement


FinancialEventType = Literal[
    "TRANSACTION",
    "ACCOUNT_TRANSFER",
    "SHOPPING_LIST",
]


class FinancialEvent(BaseModel):
    uuid: UUID
    occurred_at: int
    description: str = Field(min_length=1, max_length=300)
    type: FinancialEventType
    movements: list[FinancialMovement]

    @model_validator(mode="after")
    def validate_movement_events(self) -> Self:
        if any(movement.financial_event_uuid != self.uuid for movement in self.movements):
            raise ValueError("every movement must belong to the transaction event")
        return self
