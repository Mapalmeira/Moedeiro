from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.appearance import Icon, RgbColorCode

LedgerName = Annotated[str, Field(min_length=1, max_length=50)]
LedgerAccessTimestamp = Annotated[int, Field(ge=0)]


class Ledger(BaseModel):
    uuid: UUID
    name: LedgerName
    path: str
    icon: Icon
    color_code: RgbColorCode
    last_accessed_at: LedgerAccessTimestamp
