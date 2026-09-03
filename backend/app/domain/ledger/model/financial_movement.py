from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


FinancialMovementItemName = Annotated[str, Field(max_length=50)]


class FinancialMovement(BaseModel):
    uuid: UUID
    financial_event_uuid: UUID
    account_uuid: UUID
    category_uuid: UUID
    value: int
    item_name: FinancialMovementItemName | None = None

    @field_validator("value")
    @classmethod
    def reject_zero_value(cls, value: int) -> int:
        if value == 0:
            raise ValueError("value must not be zero")
        return value
