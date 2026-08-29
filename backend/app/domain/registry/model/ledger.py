from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.appearance import Icon, RgbColorCode

LedgerPath = Annotated[str, Field(min_length=1)]


class Ledger(BaseModel):
    uuid: UUID
    path: LedgerPath
    icon: Icon
    color_code: RgbColorCode
