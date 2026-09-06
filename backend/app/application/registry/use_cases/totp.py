from collections.abc import Callable
from uuid import UUID

from app.application.registry.exceptions import InvalidCurrentPasswordError, InvalidTotpCodeError, InvalidTotpSetupError, TotpAlreadyEnabledError, TotpCodeAlreadyUsedError, TotpNotEnabledError, TotpRequiredError
from app.application.registry.password_hasher import PasswordHasher
from app.application.registry.totp_authenticator import TotpAuthenticator
from app.application.registry.unit_of_work import RegistryUnitOfWork
from app.domain.registry.model.mfa_method import totp_setup_expires_at
from app.domain.registry.model.totp import TotpCode, TotpStatus
from app.domain.registry.model.user import Password, User


def get_totp_status(unit_of_work_factory: Callable[[], RegistryUnitOfWork], totp_authenticator: TotpAuthenticator, user: User, timestamp: int) -> TotpStatus:
    with unit_of_work_factory() as unit_of_work:
        method = unit_of_work.mfa_method_repository.get_totp_by_user(user.uuid)
        if method is None or (method.confirmed_at is None and timestamp >= method.expires_unconfirmed_at):
            return TotpStatus(state="DISABLED")
        if method.confirmed_at is not None:
            return TotpStatus(state="ENABLED")
        secret = totp_authenticator.decrypt_secret(method.secret_encrypted)
        return TotpStatus(state="PENDING", provisioning_uri=totp_authenticator.provisioning_uri(secret, user.name), expires_at=method.expires_unconfirmed_at)


def start_totp_setup(unit_of_work_factory: Callable[[], RegistryUnitOfWork], password_hasher: PasswordHasher, totp_authenticator: TotpAuthenticator, user: User, current_password: Password, timestamp: int) -> TotpStatus:
    if not password_hasher.verify(user.password_hash, current_password):
        raise InvalidCurrentPasswordError
    secret = totp_authenticator.create_secret()
    setup_expires_at = totp_setup_expires_at(timestamp)
    with unit_of_work_factory() as unit_of_work:
        method = unit_of_work.mfa_method_repository.get_totp_by_user(user.uuid)
        if method is not None and method.confirmed_at is not None:
            raise TotpAlreadyEnabledError
        if method is not None:
            unit_of_work.mfa_method_repository.delete(method.uuid)
        method = unit_of_work.mfa_method_repository.create(user.uuid, "TOTP", totp_authenticator.encrypt_secret(secret), timestamp, setup_expires_at)
        unit_of_work.commit()
    return TotpStatus(state="PENDING", provisioning_uri=totp_authenticator.provisioning_uri(secret, user.name), expires_at=method.expires_unconfirmed_at)


def confirm_totp_setup(unit_of_work_factory: Callable[[], RegistryUnitOfWork], totp_authenticator: TotpAuthenticator, user: User, code: TotpCode, timestamp: int) -> None:
    with unit_of_work_factory() as unit_of_work:
        method = unit_of_work.mfa_method_repository.get_totp_by_user(user.uuid)
        if method is None:
            raise InvalidTotpSetupError
        if method.confirmed_at is not None:
            raise TotpAlreadyEnabledError
        if timestamp < method.created_at:
            raise InvalidTotpSetupError
        if timestamp >= method.expires_unconfirmed_at:
            raise InvalidTotpSetupError
        counter = totp_authenticator.verify(totp_authenticator.decrypt_secret(method.secret_encrypted), code, timestamp)
        if counter is None:
            raise InvalidTotpCodeError
        if not unit_of_work.mfa_method_repository.confirm(method.uuid, timestamp, counter):
            raise InvalidTotpSetupError
        unit_of_work.commit()


def disable_totp(unit_of_work_factory: Callable[[], RegistryUnitOfWork], password_hasher: PasswordHasher, totp_authenticator: TotpAuthenticator, user: User, current_password: Password, code: TotpCode, timestamp: int) -> None:
    if not password_hasher.verify(user.password_hash, current_password):
        raise InvalidCurrentPasswordError
    with unit_of_work_factory() as unit_of_work:
        method = unit_of_work.mfa_method_repository.get_totp_by_user(user.uuid)
        if method is None or method.confirmed_at is None:
            raise TotpNotEnabledError
        verify_totp(unit_of_work, totp_authenticator, user.uuid, code, timestamp)
        unit_of_work.mfa_method_repository.delete(method.uuid)
        unit_of_work.commit()


def verify_totp(unit_of_work: RegistryUnitOfWork, totp_authenticator: TotpAuthenticator | None, user_uuid: UUID, code: TotpCode | None, timestamp: int) -> None:
    method = unit_of_work.mfa_method_repository.get_totp_by_user(user_uuid)
    if method is None or method.confirmed_at is None:
        return
    if code is None:
        raise TotpRequiredError
    if totp_authenticator is None:
        raise InvalidTotpCodeError
    counter = totp_authenticator.verify(totp_authenticator.decrypt_secret(method.secret_encrypted), code, timestamp)
    if counter is None:
        raise InvalidTotpCodeError
    if not unit_of_work.mfa_method_repository.use_totp_counter(method.uuid, counter):
        raise TotpCodeAlreadyUsedError
