from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.appearance import Icon
from app.domain.registry.model.ledger import Ledger, LedgerName


HexRgbColorCode = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]


class CreateLedgerRequest(BaseModel):
    name: LedgerName
    icon: Icon
    color_code: HexRgbColorCode


class UpdateLedgerRequest(BaseModel):
    name: LedgerName
    icon: Icon
    color_code: HexRgbColorCode


class LedgerResponse(BaseModel):
    uuid: UUID
    name: LedgerName
    icon: Icon
    color_code: HexRgbColorCode

    @classmethod
    def from_ledger(cls, ledger: Ledger) -> Self:
        return cls(
            uuid=ledger.uuid,
            name=ledger.name,
            icon=ledger.icon,
            color_code=f"#{ledger.color_code.hex().upper()}",
        )
