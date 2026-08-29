from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class FinancialMovement(BaseModel):
    uuid: UUID
    transaction_event_uuid: UUID
    account_uuid: UUID
    category_uuid: UUID
    value: int
    item_name: str | None = Field(default=None, max_length=30)

    @field_validator("value")
    @classmethod
    def reject_zero_value(cls, value: int) -> int:
        if value == 0:
            raise ValueError("value must not be zero")
        return value
