from collections.abc import Callable
from uuid import UUID

from app.application.registry.exceptions import UserNotFoundError
from app.application.registry.unit_of_work import RegistryUnitOfWork
from app.domain.registry.model.user_preferences import DateFormat, Language, NumberFormat, Theme, TimeFormat, Timezone, UserPreferences


def get_user_preferences(unit_of_work_factory: Callable[[], RegistryUnitOfWork], user_uuid: UUID) -> UserPreferences:
    with unit_of_work_factory() as unit_of_work:
        preferences = unit_of_work.user_preferences_repository.get(user_uuid)
    return UserPreferences(user_uuid=user_uuid) if preferences is None else preferences


def save_user_preferences(
    unit_of_work_factory: Callable[[], RegistryUnitOfWork],
    user_uuid: UUID,
    language: Language | None,
    date_format: DateFormat | None,
    time_format: TimeFormat | None,
    number_format: NumberFormat | None,
    theme: Theme | None,
    timezone: Timezone | None,
) -> UserPreferences:
    with unit_of_work_factory() as unit_of_work:
        if unit_of_work.user_repository.get(user_uuid) is None:
            raise UserNotFoundError
        preferences = unit_of_work.user_preferences_repository.save(user_uuid, language, date_format, time_format, number_format, theme, timezone)
        unit_of_work.commit()
    return preferences
