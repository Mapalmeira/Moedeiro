from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field
from typing_extensions import Self

from app.domain.appearance import Icon
from app.domain.ledger.model.currency import Currency


HexRgbColorCode = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]


class CurrencyPayload(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    prefix: str | None = Field(default=None, max_length=10)
    suffix: str | None = Field(default=None, max_length=10)
    icon: Icon
    color_code: HexRgbColorCode


class CreateCurrencyRequest(CurrencyPayload):
    decimal_places: int = Field(ge=0, le=20)


class UpdateCurrencyRequest(CurrencyPayload):
    pass


class CurrencyResponse(BaseModel):
    uuid: UUID
    name: str
    prefix: str | None
    suffix: str | None
    decimal_places: int
    icon: Icon
    color_code: HexRgbColorCode

    @classmethod
    def from_currency(cls, currency: Currency) -> Self:
        return cls(
            uuid=currency.uuid,
            name=currency.name,
            prefix=currency.prefix,
            suffix=currency.suffix,
            decimal_places=currency.decimal_places,
            icon=currency.icon,
            color_code=f"#{currency.color_code.hex().upper()}",
        )
