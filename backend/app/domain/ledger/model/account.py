from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.appearance import Icon, RgbColorCode

class Account(BaseModel):
    uuid: UUID
    name: str = Field(min_length=1, max_length=50)
    note: str | None = Field(default=None, max_length=300)
    currency_uuid: UUID
    icon: Icon
    color_code: RgbColorCode
