from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.domain.appearance import Icon, RgbColorCode


BudgetName = Annotated[str, Field(min_length=1, max_length=50)]
BudgetDescription = Annotated[str, Field(min_length=1, max_length=300)]
BudgetAmount = Annotated[int, Field(ge=0)]


class Budget(BaseModel):
    uuid: UUID
    category_uuid: UUID
    currency_uuid: UUID
    from_timestamp: int
    to_timestamp: int
    name: BudgetName
    description: BudgetDescription
    amount: BudgetAmount
    icon: Icon
    color_code: RgbColorCode
    account_uuids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_period(self) -> Self:
        if self.from_timestamp >= self.to_timestamp:
            raise ValueError("from_timestamp must be less than to_timestamp")
        return self
