from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.user_preferences import DateFormat, Language, NumberFormat, Theme, TimeFormat, Timezone, UserPreferences


class UserPreferencesRepository(ABC):
    @abstractmethod
    def get(self, user_uuid: UUID) -> UserPreferences | None:
        pass

    @abstractmethod
    def save(self, user_uuid: UUID, language: Language, date_format: DateFormat, time_format: TimeFormat, number_format: NumberFormat, theme: Theme, timezone: Timezone) -> UserPreferences:
        pass
