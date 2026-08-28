from uuid import UUID

from pydantic import BaseModel, Field, model_validator

class Budget(BaseModel):
    uuid: UUID
    category_uuid: UUID
    currency_uuid: UUID
    from_timestamp: int
    to_timestamp: int
    name: str = Field(min_length=1, max_length=30)
    description: str = Field(min_length=1, max_length=300)
    amount: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_period(self) -> "Budget":
        if self.from_timestamp >= self.to_timestamp:
            raise ValueError("from_timestamp must be less than to_timestamp")
        return self
