from collections.abc import Callable
from uuid import UUID

from app.application.registry.exceptions import LedgerLimitReachedError, LedgerNotFoundError, LedgerOwnershipAlreadyExistsError, LedgerGrantNotFoundError, UserNotFoundError
from app.application.registry.unit_of_work import RegistryUnitOfWork
from app.domain.registry.limits import MAXIMUM_LEDGERS_PER_USER
from app.domain.registry.model.ledger_grant import LedgerGrant


def list_ledger_grants(
    unit_of_work_factory: Callable[[], RegistryUnitOfWork],
    user_uuid: UUID | None = None,
    ledger_uuid: UUID | None = None,
) -> list[LedgerGrant]:
    with unit_of_work_factory() as unit_of_work:
        grants = unit_of_work.ledger_grant_repository.list_all()
    return [
        grant
        for grant in grants
        if (user_uuid is None or grant.user_uuid == user_uuid)
        and (ledger_uuid is None or grant.ledger_uuid == ledger_uuid)
    ]


def set_ledger_owner(
    unit_of_work_factory: Callable[[], RegistryUnitOfWork],
    user_uuid: UUID,
    ledger_uuid: UUID,
    timestamp: int,
) -> LedgerGrant:
    with unit_of_work_factory() as unit_of_work:
        if unit_of_work.user_repository.get(user_uuid) is None:
            raise UserNotFoundError
        if unit_of_work.ledger_repository.get(ledger_uuid) is None:
            raise LedgerNotFoundError
        if unit_of_work.ledger_grant_repository.get_active(user_uuid, ledger_uuid) is not None:
            raise LedgerOwnershipAlreadyExistsError
        if unit_of_work.ledger_repository.count_owned_by_user(user_uuid) >= MAXIMUM_LEDGERS_PER_USER:
            raise LedgerLimitReachedError
        for grant in unit_of_work.ledger_grant_repository.list_by_ledger(ledger_uuid):
            if grant.role == "OWNER" and grant.revoked_at is None:
                unit_of_work.ledger_grant_repository.revoke(grant.uuid, timestamp)
        grant = unit_of_work.ledger_grant_repository.create(user_uuid, ledger_uuid, "OWNER", timestamp)
        unit_of_work.commit()
    return grant


def revoke_ledger_grant(unit_of_work_factory: Callable[[], RegistryUnitOfWork], grant_uuid: UUID, timestamp: int) -> None:
    with unit_of_work_factory() as unit_of_work:
        grant = unit_of_work.ledger_grant_repository.get(grant_uuid)
        if grant is None or grant.revoked_at is not None:
            raise LedgerGrantNotFoundError
        unit_of_work.ledger_grant_repository.revoke(grant.uuid, timestamp)
        unit_of_work.commit()
