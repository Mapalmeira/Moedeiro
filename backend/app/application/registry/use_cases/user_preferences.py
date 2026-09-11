from collections.abc import Callable
from uuid import UUID

from app.application.registry.exceptions import UserNotFoundError, UserPreferencesNotFoundError
from app.application.registry.unit_of_work import RegistryUnitOfWork
from app.domain.registry.model.user_preferences import Language, Theme, Timezone, UserPreferences


def get_user_preferences(
    unit_of_work_factory: Callable[[], RegistryUnitOfWork],
    user_uuid: UUID,
) -> UserPreferences:
    with unit_of_work_factory() as unit_of_work:
        preferences = unit_of_work.user_preferences_repository.get(user_uuid)
        if preferences is None:
            raise UserPreferencesNotFoundError
        return preferences


def save_user_preferences(
    unit_of_work_factory: Callable[[], RegistryUnitOfWork],
    user_uuid: UUID,
    language: Language,
    theme: Theme,
    timezone: Timezone,
) -> UserPreferences:
    with unit_of_work_factory() as unit_of_work:
        if unit_of_work.user_repository.get(user_uuid) is None:
            raise UserNotFoundError
        preferences = unit_of_work.user_preferences_repository.save(user_uuid, language, theme, timezone)
        unit_of_work.commit()
    return preferences
