from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.appearance import Icon, RgbColorCode


class Currency(BaseModel):
    uuid: UUID
    name: str = Field(min_length=1, max_length=30)
    suffix: str | None = Field(default=None, max_length=10)
    prefix: str | None = Field(default=None, max_length=10)
    decimal_places: int = Field(ge=0, le=20)
    icon: Icon
    color_code: RgbColorCode
