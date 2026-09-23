from collections.abc import Callable
from uuid import UUID

from app.application.registry.secret import hash_ascii_secret
from app.application.registry.unit_of_work import RegistryUnitOfWork
from app.domain.registry.model.crockford_code import generate_crockford_code
from app.domain.registry.model.user_invitation import DEFAULT_EXPIRATION_TIMEOUT_SECONDS, InvitationCode, UserInvitation


def create_user_invitation(unit_of_work_factory: Callable[[], RegistryUnitOfWork], created_at: int, expiration_seconds: int = DEFAULT_EXPIRATION_TIMEOUT_SECONDS) -> InvitationCode:
    if expiration_seconds <= 0:
        raise ValueError("expiration_seconds must be positive")
    code = generate_crockford_code()
    secret_hash = hash_ascii_secret(code)
    with unit_of_work_factory() as unit_of_work:
        unit_of_work.user_invitation_repository.create(secret_hash, created_at, created_at + expiration_seconds)
        unit_of_work.commit()
    return code


def get_available_user_invitation(unit_of_work_factory: Callable[[], RegistryUnitOfWork], code: InvitationCode, timestamp: int) -> UserInvitation | None:
    secret_hash = hash_ascii_secret(code)
    with unit_of_work_factory() as unit_of_work:
        invitation = unit_of_work.user_invitation_repository.get_by_secret_hash(secret_hash)
    if invitation is None or invitation.created_at > timestamp or invitation.expires_at <= timestamp or invitation.consumed_at is not None:
        return None
    return invitation


def revoke_user_invitation(unit_of_work_factory: Callable[[], RegistryUnitOfWork], invitation_uuid: UUID) -> bool:
    with unit_of_work_factory() as unit_of_work:
        invitation = unit_of_work.user_invitation_repository.get(invitation_uuid)
        if invitation is None or invitation.consumed_at is not None:
            return False
        if not unit_of_work.user_invitation_repository.delete(invitation_uuid):
            return False
        unit_of_work.commit()
    return True


def list_user_invitations(unit_of_work_factory: Callable[[], RegistryUnitOfWork], sort_key: str, ascending: bool) -> list[UserInvitation]:
    with unit_of_work_factory() as unit_of_work:
        return unit_of_work.user_invitation_repository.list_all(sort_key, ascending)
