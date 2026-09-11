from typing import Self

from pydantic import BaseModel

from app.domain.registry.model.user_preferences import Language, Theme, UserPreferences


class UserPreferencesPayload(BaseModel):
    language: Language
    theme: Theme

    @classmethod
    def from_preferences(cls, preferences: UserPreferences) -> Self:
        return cls(
            language=preferences.language,
            theme=preferences.theme,
        )
