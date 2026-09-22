from collections.abc import Callable
from uuid import UUID

from app.application.registry.exceptions import UserNotFoundError
from app.application.registry.unit_of_work import RegistryUnitOfWork


def disable_mfa(unit_of_work_factory: Callable[[], RegistryUnitOfWork], user_uuid: UUID) -> int:
    with unit_of_work_factory() as unit_of_work:
        if unit_of_work.user_repository.get(user_uuid) is None:
            raise UserNotFoundError
        disabled_count = unit_of_work.mfa_method_repository.delete_by_user(user_uuid)
        if disabled_count == 0:
            return 0
        unit_of_work.auth_session_repository.delete_by_user(user_uuid)
        unit_of_work.remember_session_repository.delete_by_user(user_uuid)
        unit_of_work.commit()
    return disabled_count
