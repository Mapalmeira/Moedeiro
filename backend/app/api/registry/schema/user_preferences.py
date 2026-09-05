from typing import Self

from pydantic import BaseModel

from app.domain.registry.model.user_preferences import DateFormat, Language, NumberFormat, Theme, TimeFormat, Timezone, UserPreferences


class UserPreferencesPayload(BaseModel):
    language: Language
    date_format: DateFormat
    time_format: TimeFormat
    number_format: NumberFormat
    theme: Theme
    timezone: Timezone

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
