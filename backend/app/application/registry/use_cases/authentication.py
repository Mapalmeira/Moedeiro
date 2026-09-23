from collections.abc import Callable
from uuid import UUID

from app.application.registry.exceptions import InvalidCredentialsError, InvalidSessionError, UserNotFoundError
from app.application.registry.password_hasher import PasswordHasher
from app.application.registry.secret import generate_opaque_token, try_hash_ascii_secret
from app.application.registry.totp_authenticator import TotpAuthenticator
from app.application.registry.unit_of_work import RegistryUnitOfWork
from app.application.registry.use_cases.totp import verify_totp
from app.domain.registry.model.auth_session import DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, DEFAULT_INACTIVITY_TIMEOUT_SECONDS
from app.domain.registry.model.remember_session import DEFAULT_EXPIRATION_TIMEOUT_SECONDS
from app.domain.registry.model.totp import TotpCode
from app.domain.registry.model.user import Password, User, UserName, normalize_user_name


def login(
    unit_of_work_factory: Callable[[], RegistryUnitOfWork],
    password_hasher: PasswordHasher,
    name: UserName,
    password: Password,
    remember: bool,
    timestamp: int,
    current_session_token: str | None = None,
    current_remember_token: str | None = None,
    totp_authenticator: TotpAuthenticator | None = None,
    totp_code: TotpCode | None = None,
) -> tuple[str, str | None]:
    with unit_of_work_factory() as unit_of_work:
        user = unit_of_work.user_repository.get_by_normalized_name(normalize_user_name(name))
        if user is None:
            password_hasher.hash(password)
            raise UserNotFoundError
        if not password_hasher.verify(user.password_hash, password):
            raise InvalidCredentialsError
        verify_totp(unit_of_work, totp_authenticator, user.uuid, totp_code, timestamp)

        _delete_presented_sessions(unit_of_work, current_session_token, current_remember_token)

        session_token, session_token_hash = generate_opaque_token()
        unit_of_work.auth_session_repository.create(
            user.uuid,
            session_token_hash,
            timestamp,
            timestamp + DEFAULT_ABSOLUTE_TIMEOUT_SECONDS,
            DEFAULT_INACTIVITY_TIMEOUT_SECONDS,
        )

        remember_token = None
        if remember:
            remember_token, remember_token_hash = generate_opaque_token()
            unit_of_work.remember_session_repository.create(
                user.uuid,
                remember_token_hash,
                timestamp,
                timestamp + DEFAULT_EXPIRATION_TIMEOUT_SECONDS,
            )
        unit_of_work.commit()
    return session_token, remember_token


def authenticate_session(unit_of_work_factory: Callable[[], RegistryUnitOfWork], token: str, timestamp: int) -> User:
    session_uuid, user = resolve_session_user(unit_of_work_factory, token, timestamp)
    update_session_activity(unit_of_work_factory, session_uuid, timestamp)
    return user


def resolve_session_user(unit_of_work_factory: Callable[[], RegistryUnitOfWork], token: str, timestamp: int) -> tuple[UUID, User]:
    token_hash = try_hash_ascii_secret(token)
    if token_hash is None:
        raise InvalidSessionError
    with unit_of_work_factory() as unit_of_work:
        session = unit_of_work.auth_session_repository.get_active_by_token_hash(token_hash, timestamp)
        if session is None:
            raise InvalidSessionError
        user = unit_of_work.user_repository.get(session.user_uuid)
        if user is None:
            raise InvalidSessionError
    return session.uuid, user


def update_session_activity(unit_of_work_factory: Callable[[], RegistryUnitOfWork], session_uuid: UUID, timestamp: int) -> None:
    with unit_of_work_factory() as unit_of_work:
        if not unit_of_work.auth_session_repository.update_last_activity(session_uuid, timestamp):
            raise InvalidSessionError
        unit_of_work.commit()


def refresh_session(unit_of_work_factory: Callable[[], RegistryUnitOfWork], remember_token: str, timestamp: int) -> tuple[str, str]:
    expected_hash = try_hash_ascii_secret(remember_token)
    if expected_hash is None:
        raise InvalidSessionError
    new_remember_token, new_remember_token_hash = generate_opaque_token()
    session_token, session_token_hash = generate_opaque_token()

    with unit_of_work_factory() as unit_of_work:
        remember_session = unit_of_work.remember_session_repository.get_by_token_hash(expected_hash)
        if remember_session is None or not unit_of_work.remember_session_repository.rotate(
            remember_session.uuid,
            expected_hash,
            new_remember_token_hash,
            timestamp,
        ):
            raise InvalidSessionError
        unit_of_work.auth_session_repository.create(
            remember_session.user_uuid,
            session_token_hash,
            timestamp,
            timestamp + DEFAULT_ABSOLUTE_TIMEOUT_SECONDS,
            DEFAULT_INACTIVITY_TIMEOUT_SECONDS,
        )
        unit_of_work.commit()
    return session_token, new_remember_token


def logout(unit_of_work_factory: Callable[[], RegistryUnitOfWork], session_token: str | None, remember_token: str | None) -> None:
    with unit_of_work_factory() as unit_of_work:
        _delete_presented_sessions(unit_of_work, session_token, remember_token)
        unit_of_work.commit()


def _delete_presented_sessions(unit_of_work: RegistryUnitOfWork, session_token: str | None, remember_token: str | None) -> None:
    if session_token is not None:
        session_token_hash = try_hash_ascii_secret(session_token)
        if session_token_hash is not None:
            session = unit_of_work.auth_session_repository.get_by_token_hash(session_token_hash)
            if session is not None:
                unit_of_work.auth_session_repository.delete(session.uuid)
    if remember_token is not None:
        remember_token_hash = try_hash_ascii_secret(remember_token)
        if remember_token_hash is not None:
            remember_session = unit_of_work.remember_session_repository.get_by_token_hash(remember_token_hash)
            if remember_session is not None:
                unit_of_work.remember_session_repository.delete(remember_session.uuid)
