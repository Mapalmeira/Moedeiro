import hashlib
import secrets
from collections.abc import Callable

from app.application.registry.exceptions import InvalidCredentialsError, InvalidSessionError
from app.application.registry.unit_of_work import RegistryUnitOfWork
from app.application.services.password_hasher import PasswordHasher
from app.domain.registry.model.auth_session import DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, DEFAULT_INACTIVITY_TIMEOUT_SECONDS
from app.domain.registry.model.remember_session import DEFAULT_EXPIRATION_TIMEOUT_SECONDS
from app.domain.registry.model.user import User, normalize_user_name


def login(
    unit_of_work_factory: Callable[[], RegistryUnitOfWork],
    password_hasher: PasswordHasher,
    name: str,
    password: str,
    remember: bool,
    timestamp: int,
    current_session_token: str | None = None,
    current_remember_token: str | None = None,
) -> tuple[str, str | None]:
    with unit_of_work_factory() as unit_of_work:
        user = unit_of_work.user_repository.get_by_normalized_name(normalize_user_name(name))
        if user is None or not password_hasher.verify(user.password_hash, password):
            raise InvalidCredentialsError

        _revoke_presented_sessions(unit_of_work, current_session_token, current_remember_token, timestamp)

        session_token = secrets.token_urlsafe(32)
        unit_of_work.auth_session_repository.create(
            user.uuid,
            _token_hash(session_token),
            timestamp,
            timestamp + DEFAULT_ABSOLUTE_TIMEOUT_SECONDS,
            DEFAULT_INACTIVITY_TIMEOUT_SECONDS,
        )

        remember_token = None
        if remember:
            remember_token = secrets.token_urlsafe(32)
            unit_of_work.remember_session_repository.create(
                user.uuid,
                _token_hash(remember_token),
                timestamp,
                timestamp + DEFAULT_EXPIRATION_TIMEOUT_SECONDS,
            )
        unit_of_work.commit()
    return session_token, remember_token


def authenticate_session(unit_of_work_factory: Callable[[], RegistryUnitOfWork], token: str, timestamp: int) -> User:
    with unit_of_work_factory() as unit_of_work:
        session = unit_of_work.auth_session_repository.get_by_token_hash(_token_hash(token))
        if session is None or not unit_of_work.auth_session_repository.update_last_activity(session.uuid, timestamp):
            raise InvalidSessionError
        user = unit_of_work.user_repository.get(session.user_uuid)
        if user is None:
            raise InvalidSessionError
        unit_of_work.commit()
    return user


def refresh_session(unit_of_work_factory: Callable[[], RegistryUnitOfWork], remember_token: str, timestamp: int) -> tuple[str, str]:
    expected_hash = _token_hash(remember_token)
    new_remember_token = secrets.token_urlsafe(32)
    session_token = secrets.token_urlsafe(32)

    with unit_of_work_factory() as unit_of_work:
        remember_session = unit_of_work.remember_session_repository.get_by_token_hash(expected_hash)
        if remember_session is None or not unit_of_work.remember_session_repository.rotate(
            remember_session.uuid,
            expected_hash,
            _token_hash(new_remember_token),
            timestamp,
        ):
            raise InvalidSessionError
        unit_of_work.auth_session_repository.create(
            remember_session.user_uuid,
            _token_hash(session_token),
            timestamp,
            timestamp + DEFAULT_ABSOLUTE_TIMEOUT_SECONDS,
            DEFAULT_INACTIVITY_TIMEOUT_SECONDS,
        )
        unit_of_work.commit()
    return session_token, new_remember_token


def logout(unit_of_work_factory: Callable[[], RegistryUnitOfWork], session_token: str | None, remember_token: str | None, timestamp: int) -> None:
    with unit_of_work_factory() as unit_of_work:
        _revoke_presented_sessions(unit_of_work, session_token, remember_token, timestamp)
        unit_of_work.commit()


def _revoke_presented_sessions(unit_of_work: RegistryUnitOfWork, session_token: str | None, remember_token: str | None, timestamp: int) -> None:
    if session_token is not None:
        session = unit_of_work.auth_session_repository.get_by_token_hash(_token_hash(session_token))
        if session is not None:
            unit_of_work.auth_session_repository.revoke(session.uuid, timestamp)
    if remember_token is not None:
        remember_session = unit_of_work.remember_session_repository.get_by_token_hash(_token_hash(remember_token))
        if remember_session is not None:
            unit_of_work.remember_session_repository.revoke(remember_session.uuid, timestamp)


def _token_hash(token: str) -> bytes:
    return hashlib.sha256(token.encode("ascii")).digest()
