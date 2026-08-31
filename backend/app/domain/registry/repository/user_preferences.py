from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.user_preferences import Theme, UserPreferences


class UserPreferencesRepository(ABC):
    @abstractmethod
    def get(self, user_uuid: UUID) -> UserPreferences | None:
        pass

    @abstractmethod
    def save(self, user_uuid: UUID, date_format: str | None, time_format: str | None, number_format: str | None, theme: Theme | None, timezone: str | None) -> UserPreferences:
        pass
