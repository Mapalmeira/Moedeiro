from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field


ShortFormat = Annotated[str, Field(min_length=1)]
Timezone = Annotated[str, Field(min_length=1)]
Theme = Literal["LIGHT", "DARK"]


class UserPreferences(BaseModel):
    user_uuid: UUID
    date_format: ShortFormat | None = None
    time_format: ShortFormat | None = None
    number_format: ShortFormat | None = None
    theme: Theme | None = None
    timezone: Timezone | None = None
