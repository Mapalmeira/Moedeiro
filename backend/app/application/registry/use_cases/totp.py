import hashlib
from collections.abc import Callable
from uuid import UUID

from app.application.registry.exceptions import InvalidCurrentPasswordError, InvalidTotpCodeError, InvalidTotpSetupError, TotpAlreadyEnabledError, TotpNotEnabledError
from app.application.registry.password_hasher import PasswordHasher
from app.application.registry.totp_authenticator import TotpAuthenticator
from app.application.registry.unit_of_work import RegistryUnitOfWork
from app.domain.registry.model.crockford_code import CrockfordCode, generate_crockford_code
from app.domain.registry.model.totp import TotpCode
from app.domain.registry.model.user import Password, User


RECOVERY_CODE_COUNT = 10


def start_totp_setup(unit_of_work_factory: Callable[[], RegistryUnitOfWork], password_hasher: PasswordHasher, totp_authenticator: TotpAuthenticator, user: User, current_password: Password, timestamp: int) -> str:
    if not password_hasher.verify(user.password_hash, current_password):
        raise InvalidCurrentPasswordError
    secret = totp_authenticator.create_secret()
    with unit_of_work_factory() as unit_of_work:
        method = unit_of_work.mfa_method_repository.get_totp_by_user(user.uuid)
        if method is not None and method.confirmed_at is not None:
            raise TotpAlreadyEnabledError
        if method is not None:
            unit_of_work.mfa_method_repository.delete(method.uuid)
        unit_of_work.mfa_method_repository.create(user.uuid, "TOTP", totp_authenticator.encrypt_secret(secret), timestamp)
        unit_of_work.commit()
    return totp_authenticator.provisioning_uri(secret, user.name)


def enable_totp(unit_of_work_factory: Callable[[], RegistryUnitOfWork], totp_authenticator: TotpAuthenticator, user: User, code: TotpCode, timestamp: int) -> list[CrockfordCode]:
    with unit_of_work_factory() as unit_of_work:
        method = unit_of_work.mfa_method_repository.get_totp_by_user(user.uuid)
        if method is None:
            raise InvalidTotpSetupError
        if method.confirmed_at is not None:
            raise TotpAlreadyEnabledError
        if not totp_authenticator.verify(totp_authenticator.decrypt_secret(method.secret_encrypted), code, timestamp):
            raise InvalidTotpCodeError
        if not unit_of_work.mfa_method_repository.confirm(method.uuid, timestamp):
            raise InvalidTotpSetupError
        recovery_codes = [generate_crockford_code() for _ in range(RECOVERY_CODE_COUNT)]
        for recovery_code in recovery_codes:
            unit_of_work.recovery_code_repository.create(user.uuid, _recovery_code_hash(recovery_code), timestamp)
        unit_of_work.commit()
    return recovery_codes


def verify_totp(unit_of_work: RegistryUnitOfWork, totp_authenticator: TotpAuthenticator | None, user_uuid: UUID, code: TotpCode | None, timestamp: int) -> None:
    method = unit_of_work.mfa_method_repository.get_totp_by_user(user_uuid)
    if method is None or method.confirmed_at is None:
        return
    if totp_authenticator is None or code is None or not totp_authenticator.verify(totp_authenticator.decrypt_secret(method.secret_encrypted), code, timestamp):
        raise InvalidTotpCodeError


def disable_totp(unit_of_work_factory: Callable[[], RegistryUnitOfWork], totp_authenticator: TotpAuthenticator, user: User, code: TotpCode, timestamp: int) -> None:
    with unit_of_work_factory() as unit_of_work:
        method = unit_of_work.mfa_method_repository.get_totp_by_user(user.uuid)
        if method is None or method.confirmed_at is None:
            raise TotpNotEnabledError
        if not totp_authenticator.verify(totp_authenticator.decrypt_secret(method.secret_encrypted), code, timestamp):
            raise InvalidTotpCodeError
        unit_of_work.mfa_method_repository.delete(method.uuid)
        _revoke_user_sessions(unit_of_work, user.uuid, timestamp)
        unit_of_work.commit()


def _recovery_code_hash(code: CrockfordCode) -> bytes:
    return hashlib.sha256(code.encode("ascii")).digest()


def _revoke_user_sessions(unit_of_work: RegistryUnitOfWork, user_uuid: UUID, timestamp: int) -> None:
    unit_of_work.auth_session_repository.revoke_by_user(user_uuid, timestamp)
    unit_of_work.remember_session_repository.revoke_by_user(user_uuid, timestamp)
