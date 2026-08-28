from uuid import UUID

from pydantic import BaseModel, Field


class FinancialMovement(BaseModel):
    uuid: UUID
    transaction_event_uuid: UUID
    account_uuid: UUID
    category_uuid: UUID
    value: int
    item_name: str | None = Field(default=None, max_length=30)
