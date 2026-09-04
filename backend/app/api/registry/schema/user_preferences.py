from typing import Self

from pydantic import BaseModel

from app.domain.registry.model.user_preferences import ShortFormat, Theme, Timezone, UserPreferences


class UpdateUserPreferencesRequest(BaseModel):
    date_format: ShortFormat | None = None
    time_format: ShortFormat | None = None
    number_format: ShortFormat | None = None
    theme: Theme | None = None
    timezone: Timezone | None = None


class UserPreferencesResponse(BaseModel):
    date_format: ShortFormat | None
    time_format: ShortFormat | None
    number_format: ShortFormat | None
    theme: Theme | None
    timezone: Timezone | None

    @classmethod
    def from_preferences(cls, preferences: UserPreferences) -> Self:
        return cls(
            date_format=preferences.date_format,
            time_format=preferences.time_format,
            number_format=preferences.number_format,
            theme=preferences.theme,
            timezone=preferences.timezone,
        )
