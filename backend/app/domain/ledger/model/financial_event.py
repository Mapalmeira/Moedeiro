from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from app.domain.ledger.model.financial_movement import FinancialMovement


FinancialEventType = Literal[
    "TRANSACTION",
    "ACCOUNT_TRANSFER",
    "SHOPPING_LIST",
]
FinancialEventDescription = Annotated[str, Field(min_length=1, max_length=300)]


class FinancialEvent(BaseModel):
    uuid: UUID
    occurred_at: int
    description: FinancialEventDescription
    type: FinancialEventType
    movements: list[FinancialMovement]

    @model_validator(mode="after")
    def validate_movement_events(self) -> Self:
        if any(movement.financial_event_uuid != self.uuid for movement in self.movements):
            raise ValueError("every movement must belong to the financial event")
        return self
