from typing import Self

from pydantic import BaseModel

from app.domain.registry.model.user_preferences import DateFormat, Language, NumberFormat, Theme, TimeFormat, Timezone, UserPreferences


class UserPreferencesPayload(BaseModel):
    language: Language | None = None
    date_format: DateFormat | None = None
    time_format: TimeFormat | None = None
    number_format: NumberFormat | None = None
    theme: Theme | None = None
    timezone: Timezone | None = None

    @classmethod
    def from_preferences(cls, preferences: UserPreferences) -> Self:
        return cls(
            language=preferences.language,
            date_format=preferences.date_format,
            time_format=preferences.time_format,
            number_format=preferences.number_format,
            theme=preferences.theme,
            timezone=preferences.timezone,
        )
