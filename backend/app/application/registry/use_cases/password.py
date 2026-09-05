import hashlib
import hmac
from collections.abc import Callable
from uuid import UUID

from app.application.registry.exceptions import InvalidCurrentPasswordError, PasswordUpdateConflictError, RecoveryCodeNotAvailableError, UserNotFoundError
from app.application.registry.password_hasher import PasswordHasher
from app.application.registry.totp_authenticator import TotpAuthenticator
from app.application.registry.unit_of_work import RegistryUnitOfWork
from app.application.registry.use_cases.totp import verify_totp
from app.domain.registry.model.crockford_code import generate_crockford_code
from app.domain.registry.model.recovery_code import DEFAULT_EXPIRATION_TIMEOUT_SECONDS, RecoveryCodeValue
from app.domain.registry.model.totp import TotpCode
from app.domain.registry.model.user import Password, User, UserName, normalize_user_name


def change_password(unit_of_work_factory: Callable[[], RegistryUnitOfWork], password_hasher: PasswordHasher, user: User, current_password: Password, new_password: Password, timestamp: int, totp_authenticator: TotpAuthenticator | None = None, totp_code: TotpCode | None = None) -> None:
    if not password_hasher.verify(user.password_hash, current_password):
        raise InvalidCurrentPasswordError

    with unit_of_work_factory() as unit_of_work:
        verify_totp(unit_of_work, totp_authenticator, user.uuid, totp_code, timestamp)
        new_password_hash = password_hasher.hash(new_password)
        if not unit_of_work.user_repository.update_password(user.uuid, user.password_hash, new_password_hash, timestamp):
            if unit_of_work.user_repository.get(user.uuid) is None:
                raise UserNotFoundError
            raise PasswordUpdateConflictError
        _delete_user_sessions(unit_of_work, user.uuid)
        unit_of_work.commit()


def create_recovery_code(unit_of_work_factory: Callable[[], RegistryUnitOfWork], user_uuid: UUID, timestamp: int, expiration_seconds: int = DEFAULT_EXPIRATION_TIMEOUT_SECONDS) -> RecoveryCodeValue:
    if expiration_seconds <= 0:
        raise ValueError("expiration_seconds must be positive")
    code = generate_crockford_code(10)
    with unit_of_work_factory() as unit_of_work:
        if unit_of_work.user_repository.get(user_uuid) is None:
            raise UserNotFoundError
        unit_of_work.recovery_code_repository.delete_active_by_user(user_uuid)
        unit_of_work.recovery_code_repository.create(user_uuid, _code_hash(code), timestamp, timestamp + expiration_seconds)
        unit_of_work.commit()
    return code


def recover_password(unit_of_work_factory: Callable[[], RegistryUnitOfWork], password_hasher: PasswordHasher, totp_authenticator: TotpAuthenticator, name: UserName, code: RecoveryCodeValue, new_password: Password, totp_code: TotpCode | None, timestamp: int) -> None:
    new_password_hash = password_hasher.hash(new_password)
    with unit_of_work_factory() as unit_of_work:
        user = unit_of_work.user_repository.get_by_normalized_name(normalize_user_name(name))
        if user is None:
            raise UserNotFoundError
        recovery_code = unit_of_work.recovery_code_repository.get_active_by_user(user.uuid, timestamp)
        if recovery_code is None or not hmac.compare_digest(recovery_code.code_hash, _code_hash(code)):
            raise RecoveryCodeNotAvailableError
        verify_totp(unit_of_work, totp_authenticator, user.uuid, totp_code, timestamp)
        if not unit_of_work.recovery_code_repository.consume(recovery_code.uuid, timestamp):
            raise RecoveryCodeNotAvailableError
        if not unit_of_work.user_repository.update_password(user.uuid, user.password_hash, new_password_hash, timestamp):
            raise PasswordUpdateConflictError
        _delete_user_sessions(unit_of_work, user.uuid)
        unit_of_work.commit()


def _delete_user_sessions(unit_of_work: RegistryUnitOfWork, user_uuid: UUID) -> None:
    unit_of_work.auth_session_repository.delete_by_user(user_uuid)
    unit_of_work.remember_session_repository.delete_by_user(user_uuid)


def _code_hash(code: str) -> bytes:
    return hashlib.sha256(code.encode("ascii")).digest()
