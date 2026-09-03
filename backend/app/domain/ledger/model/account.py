from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.appearance import Icon, RgbColorCode

AccountName = Annotated[str, Field(min_length=1, max_length=50)]
AccountNote = Annotated[str, Field(max_length=300)]


class Account(BaseModel):
    uuid: UUID
    name: AccountName
    note: AccountNote | None = None
    currency_uuid: UUID
    icon: Icon
    color_code: RgbColorCode
