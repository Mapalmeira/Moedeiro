from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.user_preferences import DateFormat, NumberFormat, Theme, TimeFormat, Timezone, UserPreferences


class UserPreferencesRepository(ABC):
    @abstractmethod
    def get(self, user_uuid: UUID) -> UserPreferences | None:
        pass

    @abstractmethod
    def save(self, user_uuid: UUID, date_format: DateFormat | None, time_format: TimeFormat | None, number_format: NumberFormat | None, theme: Theme | None, timezone: Timezone | None) -> UserPreferences:
        pass
