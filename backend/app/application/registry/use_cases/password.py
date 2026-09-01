import hashlib
from collections.abc import Callable
from uuid import UUID

from app.application.registry.exceptions import InvalidCurrentPasswordError, RecoveryCodeNotAvailableError, UserNotFoundError
from app.application.registry.password_hasher import PasswordHasher
from app.application.registry.totp_authenticator import TotpAuthenticator
from app.application.registry.unit_of_work import RegistryUnitOfWork
from app.application.registry.use_cases.totp import verify_totp
from app.domain.registry.model.crockford_code import CrockfordCode, generate_crockford_code
from app.domain.registry.model.recovery_code import RecoveryCode
from app.domain.registry.model.totp import TotpCode
from app.domain.registry.model.user import Password, User


def change_password(unit_of_work_factory: Callable[[], RegistryUnitOfWork], password_hasher: PasswordHasher, user: User, current_password: Password, new_password: Password, timestamp: int, totp_authenticator: TotpAuthenticator | None = None, totp_code: TotpCode | None = None) -> None:
    if not password_hasher.verify(user.password_hash, current_password):
        raise InvalidCurrentPasswordError
    new_password_hash = password_hasher.hash(new_password)

    with unit_of_work_factory() as unit_of_work:
        verify_totp(unit_of_work, totp_authenticator, user.uuid, totp_code, timestamp)
        if not unit_of_work.user_repository.update_password(user.uuid, user.password_hash, new_password_hash, timestamp):
            raise InvalidCurrentPasswordError
        _revoke_user_sessions(unit_of_work, user.uuid, timestamp)
        unit_of_work.commit()


def create_recovery_code(unit_of_work_factory: Callable[[], RegistryUnitOfWork], user_uuid: UUID, timestamp: int) -> CrockfordCode:
    code = generate_crockford_code()
    with unit_of_work_factory() as unit_of_work:
        if unit_of_work.user_repository.get(user_uuid) is None:
            raise UserNotFoundError
        unit_of_work.recovery_code_repository.create(user_uuid, _code_hash(code), timestamp)
        unit_of_work.commit()
    return code


def get_available_recovery_code(unit_of_work_factory: Callable[[], RegistryUnitOfWork], code: CrockfordCode, timestamp: int) -> RecoveryCode | None:
    with unit_of_work_factory() as unit_of_work:
        recovery_code = unit_of_work.recovery_code_repository.get_by_code_hash(_code_hash(code))
    if recovery_code is None or recovery_code.created_at > timestamp or recovery_code.used_at is not None or recovery_code.revoked_at is not None:
        return None
    return recovery_code


def reset_password(unit_of_work_factory: Callable[[], RegistryUnitOfWork], password_hasher: PasswordHasher, code: CrockfordCode, new_password: Password, timestamp: int) -> None:
    new_password_hash = password_hasher.hash(new_password)
    with unit_of_work_factory() as unit_of_work:
        recovery_code = unit_of_work.recovery_code_repository.get_by_code_hash(_code_hash(code))
        if recovery_code is None or not unit_of_work.recovery_code_repository.consume(recovery_code.uuid, timestamp):
            raise RecoveryCodeNotAvailableError
        user = unit_of_work.user_repository.get(recovery_code.user_uuid)
        if user is None or not unit_of_work.user_repository.update_password(user.uuid, user.password_hash, new_password_hash, timestamp):
            raise RecoveryCodeNotAvailableError
        _revoke_user_sessions(unit_of_work, user.uuid, timestamp)
        unit_of_work.commit()


def revoke_recovery_code(unit_of_work_factory: Callable[[], RegistryUnitOfWork], recovery_code_uuid: UUID, timestamp: int) -> bool:
    with unit_of_work_factory() as unit_of_work:
        recovery_code = unit_of_work.recovery_code_repository.get(recovery_code_uuid)
        if recovery_code is None or recovery_code.used_at is not None or recovery_code.revoked_at is not None:
            return False
        unit_of_work.recovery_code_repository.revoke(recovery_code_uuid, timestamp)
        unit_of_work.commit()
    return True


def list_recovery_codes(unit_of_work_factory: Callable[[], RegistryUnitOfWork], user_uuid: UUID) -> list[RecoveryCode]:
    with unit_of_work_factory() as unit_of_work:
        return unit_of_work.recovery_code_repository.list_by_user(user_uuid)


def _revoke_user_sessions(unit_of_work: RegistryUnitOfWork, user_uuid: UUID, timestamp: int) -> None:
    unit_of_work.auth_session_repository.revoke_by_user(user_uuid, timestamp)
    unit_of_work.remember_session_repository.revoke_by_user(user_uuid, timestamp)


def _code_hash(code: CrockfordCode) -> bytes:
    return hashlib.sha256(code.encode("ascii")).digest()
