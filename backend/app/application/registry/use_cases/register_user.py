import hashlib
from collections.abc import Callable

from app.application.registry.exceptions import InvitationNotAvailableError, UserNameUnavailableError
from app.application.registry.unit_of_work import RegistryUnitOfWork
from app.application.services.password_hasher import PasswordHasher
from app.domain.registry.model.user import User, normalize_user_name


def register_user(unit_of_work_factory: Callable[[], RegistryUnitOfWork], password_hasher: PasswordHasher, invitation_code: str, name: str, password: str, timestamp: int) -> User:
    invitation_hash = hashlib.sha256(invitation_code.encode("ascii")).digest()
    normalized_name = normalize_user_name(name)
    password_hash = password_hasher.hash(password)

    with unit_of_work_factory() as unit_of_work:
        invitation = unit_of_work.user_invitation_repository.get_by_secret_hash(invitation_hash)
        if invitation is None or not unit_of_work.user_invitation_repository.consume(invitation.uuid, timestamp):
            raise InvitationNotAvailableError
        if unit_of_work.user_repository.get_by_normalized_name(normalized_name) is not None:
            raise UserNameUnavailableError
        user = unit_of_work.user_repository.create(name, password_hash, timestamp)
        unit_of_work.commit()
    return user
