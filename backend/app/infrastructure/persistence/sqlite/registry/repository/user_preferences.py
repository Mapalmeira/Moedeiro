import sqlite3
from uuid import UUID

from app.domain.registry.model.user_preferences import Language, Theme, Timezone, UserPreferences
from app.domain.registry.repository.user_preferences import UserPreferencesRepository


class SqliteUserPreferencesRepository(UserPreferencesRepository):
    _columns = "user_uuid, language, theme, timezone"

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def get(self, user_uuid: UUID) -> UserPreferences | None:
        row = self.connection.execute(f"SELECT {self._columns} FROM user_preferences WHERE user_uuid = ?", (user_uuid.bytes,)).fetchone()
        return None if row is None else UserPreferences.model_validate(dict(row))

    def save(self, user_uuid: UUID, language: Language, theme: Theme, timezone: Timezone) -> UserPreferences:
        preferences = UserPreferences(user_uuid=user_uuid, language=language, theme=theme, timezone=timezone)
        self.connection.execute(
            "INSERT INTO user_preferences(user_uuid, language, theme, timezone) VALUES (?, ?, ?, ?) ON CONFLICT(user_uuid) DO UPDATE SET language = excluded.language, theme = excluded.theme, timezone = excluded.timezone",
            (preferences.user_uuid.bytes, preferences.language, preferences.theme, preferences.timezone),
        )
        return preferences
