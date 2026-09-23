from collections.abc import Callable
from uuid import UUID

from app.application.registry.exceptions import ExternalAccessNotFoundError
from app.application.registry.unit_of_work import RegistryUnitOfWork
from app.domain.registry.model.external_access import ExternalAccess


def list_external_accesses(
    unit_of_work_factory: Callable[[], RegistryUnitOfWork],
) -> list[ExternalAccess]:
    with unit_of_work_factory() as unit_of_work:
        return unit_of_work.external_access_repository.list_all()


def delete_external_access(
    unit_of_work_factory: Callable[[], RegistryUnitOfWork],
    external_access_uuid: UUID,
) -> None:
    with unit_of_work_factory() as unit_of_work:
        if not unit_of_work.external_access_repository.delete(external_access_uuid):
            raise ExternalAccessNotFoundError
        unit_of_work.commit()
