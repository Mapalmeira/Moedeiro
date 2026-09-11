from typing import Self

from pydantic import BaseModel

from app.domain.registry.model.user_preferences import Language, Theme, Timezone, UserPreferences


class UserPreferencesPayload(BaseModel):
    language: Language
    theme: Theme
    timezone: Timezone

    @classmethod
    def from_preferences(cls, preferences: UserPreferences) -> Self:
        return cls(
            language=preferences.language,
            theme=preferences.theme,
            timezone=preferences.timezone,
        )
