from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, BaseModel, Field


DateFormat = Literal["DMY", "MDY", "YMD"]
TimeFormat = Literal["H12", "H24"]
NumberFormat = Literal["COMMA", "DOT"]
Theme = Literal["LIGHT", "DARK"]
Language = Literal["pt-BR", "en"]


def _validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as error:
        raise ValueError("timezone must be an IANA timezone name") from error
    return value


Timezone = Annotated[str, Field(min_length=1, max_length=50), AfterValidator(_validate_timezone)]


class UserPreferences(BaseModel):
    user_uuid: UUID
    language: Language | None = None
    date_format: DateFormat | None = None
    time_format: TimeFormat | None = None
    number_format: NumberFormat | None = None
    theme: Theme | None = None
    timezone: Timezone | None = None
