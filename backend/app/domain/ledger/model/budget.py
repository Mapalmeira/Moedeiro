from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

BudgetName = Annotated[str, Field(min_length=1, max_length=50)]
BudgetDescription = Annotated[str, Field(min_length=1, max_length=300)]
BudgetAmount = Annotated[int, Field(ge=0)]


class Budget(BaseModel):
    uuid: UUID
    account_uuid: UUID
    category_uuid: UUID
    from_timestamp: int
    to_timestamp: int
    name: BudgetName
    description: BudgetDescription
    amount: BudgetAmount

    @model_validator(mode="after")
    def validate_period(self) -> Self:
        if self.from_timestamp >= self.to_timestamp:
            raise ValueError("from_timestamp must be less than to_timestamp")
        return self
