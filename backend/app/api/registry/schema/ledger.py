from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field
from typing_extensions import Self

from app.domain.appearance import Icon
from app.domain.registry.model.ledger import Ledger, LedgerName


HexRgbColorCode = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]
LedgerSortKey = Literal["name", "last_accessed_at"]


class LedgerPayload(BaseModel):
    name: LedgerName
    icon: Icon
    color_code: HexRgbColorCode


CreateLedgerRequest = LedgerPayload
UpdateLedgerRequest = LedgerPayload


class LedgerResponse(BaseModel):
    uuid: UUID
    name: LedgerName
    icon: Icon
    color_code: HexRgbColorCode
    last_accessed_at: int

    @classmethod
    def from_ledger(cls, ledger: Ledger) -> Self:
        return cls(
            uuid=ledger.uuid,
            name=ledger.name,
            icon=ledger.icon,
            color_code=f"#{ledger.color_code.hex().upper()}",
            last_accessed_at=ledger.last_accessed_at,
        )
