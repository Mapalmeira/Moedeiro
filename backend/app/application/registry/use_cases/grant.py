import hashlib
import secrets
from collections.abc import Callable
from uuid import UUID

from app.application.registry.exceptions import InvalidCurrentPasswordError, LedgerGrantNotFoundError, LedgerLimitReachedError, LedgerNotFoundError, LedgerOwnershipAlreadyExistsError, UserNotFoundError
from app.application.registry.password_hasher import PasswordHasher
from app.application.registry.totp_authenticator import TotpAuthenticator
from app.application.registry.unit_of_work import RegistryUnitOfWork
from app.application.registry.use_cases.totp import verify_totp
from app.domain.registry.limits import MAXIMUM_LEDGERS_PER_USER
from app.domain.registry.model.ledger_grant import LedgerGrant
from app.domain.registry.model.totp import TotpCode
from app.domain.registry.model.user import Password, User


def list_ledger_grants(
    unit_of_work_factory: Callable[[], RegistryUnitOfWork],
    grantee_uuid: UUID | None = None,
    ledger_uuid: UUID | None = None,
) -> list[LedgerGrant]:
    with unit_of_work_factory() as unit_of_work:
        if grantee_uuid is not None and ledger_uuid is not None:
            return unit_of_work.ledger_grant_repository.list_by_grantee_and_ledger(grantee_uuid, ledger_uuid)
        if grantee_uuid is not None:
            return unit_of_work.ledger_grant_repository.list_by_grantee(grantee_uuid)
        if ledger_uuid is not None:
            return unit_of_work.ledger_grant_repository.list_by_ledger(ledger_uuid)
        return unit_of_work.ledger_grant_repository.list_all()


def create_external_ledger_grant(
    unit_of_work_factory: Callable[[], RegistryUnitOfWork],
    password_hasher: PasswordHasher,
    user: User,
    ledger_uuid: UUID,
    name: str,
    current_password: Password,
    timestamp: int,
    totp_authenticator: TotpAuthenticator | None = None,
    totp_code: TotpCode | None = None,
) -> tuple[LedgerGrant, str]:
    if not password_hasher.verify(user.password_hash, current_password):
        raise InvalidCurrentPasswordError

    with unit_of_work_factory() as unit_of_work:
        owner = unit_of_work.ledger_grant_repository.get_active_owner_by_ledger(ledger_uuid)
        if owner is None or owner.grantee_uuid != user.uuid:
            raise LedgerNotFoundError
        verify_totp(unit_of_work, totp_authenticator, user.uuid, totp_code, timestamp)
        token = secrets.token_urlsafe(32)
        access = unit_of_work.external_access_repository.create(name, _token_hash(token))
        grant = unit_of_work.ledger_grant_repository.create(access.uuid, ledger_uuid, "GUEST", timestamp)
        unit_of_work.commit()
    return grant, token


def revoke_owned_ledger_grant(
    unit_of_work_factory: Callable[[], RegistryUnitOfWork],
    password_hasher: PasswordHasher,
    user: User,
    grant_uuid: UUID,
    current_password: Password,
    timestamp: int,
    totp_authenticator: TotpAuthenticator | None = None,
    totp_code: TotpCode | None = None,
) -> None:
    if not password_hasher.verify(user.password_hash, current_password):
        raise InvalidCurrentPasswordError

    with unit_of_work_factory() as unit_of_work:
        grant = unit_of_work.ledger_grant_repository.get(grant_uuid)
        if grant is None or grant.role != "GUEST" or grant.revoked_at is not None:
            raise LedgerGrantNotFoundError
        owner = unit_of_work.ledger_grant_repository.get_active_owner_by_ledger(grant.ledger_uuid)
        if owner is None or owner.grantee_uuid != user.uuid:
            raise LedgerGrantNotFoundError
        verify_totp(unit_of_work, totp_authenticator, user.uuid, totp_code, timestamp)
        unit_of_work.ledger_grant_repository.revoke(grant_uuid, timestamp)
        unit_of_work.commit()


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
        active_owner = unit_of_work.ledger_grant_repository.get_active_owner_by_ledger(ledger_uuid)
        if active_owner is not None and active_owner.grantee_uuid == user_uuid:
            raise LedgerOwnershipAlreadyExistsError
        if unit_of_work.ledger_repository.count_owned_by_user(user_uuid) >= MAXIMUM_LEDGERS_PER_USER:
            raise LedgerLimitReachedError
        if active_owner is not None:
            unit_of_work.ledger_grant_repository.revoke(active_owner.uuid, timestamp)
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


def _token_hash(token: str) -> bytes:
    return hashlib.sha256(token.encode("ascii")).digest()
