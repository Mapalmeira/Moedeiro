from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.user_preferences import ShortFormat, Theme, Timezone, UserPreferences


class UserPreferencesRepository(ABC):
    @abstractmethod
    def get(self, user_uuid: UUID) -> UserPreferences | None:
        pass

    @abstractmethod
    def save(self, user_uuid: UUID, date_format: ShortFormat | None, time_format: ShortFormat | None, number_format: ShortFormat | None, theme: Theme | None, timezone: Timezone | None) -> UserPreferences:
        pass
