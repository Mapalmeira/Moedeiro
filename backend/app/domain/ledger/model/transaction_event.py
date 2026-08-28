from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from app.domain.ledger.model.financial_movement import FinancialMovement


TransactionEventType = Literal[
    "TRANSACTION",
    "ACCOUNT_TRANSFER",
    "SHOPPING_LIST",
]


class TransactionEvent(BaseModel):
    uuid: UUID
    occurred_at: int
    description: str = Field(min_length=1, max_length=300)
    type: TransactionEventType
    movements: list[FinancialMovement]

    @model_validator(mode="after")
    def validate_movement_events(self) -> "TransactionEvent":
        if any(movement.transaction_event_uuid != self.uuid for movement in self.movements):
            raise ValueError("every movement must belong to the transaction event")
        return self
