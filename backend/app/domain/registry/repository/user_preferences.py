from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.user_preferences import Language, Theme, Timezone, UserPreferences


class UserPreferencesRepository(ABC):
    @abstractmethod
    def get(self, user_uuid: UUID) -> UserPreferences | None:
        pass

    @abstractmethod
    def save(self, user_uuid: UUID, language: Language, theme: Theme, timezone: Timezone) -> UserPreferences:
        pass
