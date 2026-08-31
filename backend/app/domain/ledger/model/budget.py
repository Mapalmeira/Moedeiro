from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.domain.appearance import Icon, RgbColorCode

class Budget(BaseModel):
    uuid: UUID
    category_uuid: UUID
    currency_uuid: UUID
    from_timestamp: int
    to_timestamp: int
    name: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=300)
    amount: int = Field(ge=0)
    icon: Icon
    color_code: RgbColorCode

    @model_validator(mode="after")
    def validate_period(self) -> Self:
        if self.from_timestamp >= self.to_timestamp:
            raise ValueError("from_timestamp must be less than to_timestamp")
        return self
