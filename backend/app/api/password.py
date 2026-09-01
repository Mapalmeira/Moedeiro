import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.authentication import clear_authentication_cookies, require_authenticated_user
from app.api.schema.password import ChangePasswordRequest, ResetPasswordRequest, ValidateRecoveryCodeRequest
from app.application.registry.exceptions import InvalidCurrentPasswordError, InvalidTotpCodeError, RecoveryCodeNotAvailableError
from app.application.registry.password_hasher import PasswordHasher
from app.application.registry.use_cases.password import change_password, get_available_recovery_code, reset_password
from app.domain.registry.model.user import User
from app.infrastructure.persistence.sqlite.databases import SqliteDatabases
from app.infrastructure.security.rate_limiter import RateLimitExceededError, RateLimiter
from app.settings import Settings


router = APIRouter(prefix="/api/password", tags=["password"])


@router.post("/change", status_code=status.HTTP_204_NO_CONTENT)
def change_current_password(payload: ChangePasswordRequest, request: Request, response: Response, user: Annotated[User, Depends(require_authenticated_user)]) -> None:
    semaphore = request.app.state.password_hash_semaphore
    if not semaphore.acquire(blocking=False):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Password hashing capacity exhausted", headers={"Retry-After": "1"})
    try:
        change_password(
            _databases(request).open_registry,
            _password_hasher(request),
            user,
            payload.current_password,
            payload.new_password,
            int(time.time()),
            _totp_authenticator(request),
            payload.totp_code,
        )
    except (InvalidCurrentPasswordError, InvalidTotpCodeError) as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid current password") from error
    finally:
        semaphore.release()
    clear_authentication_cookies(response)


@router.post("/recovery/validate", status_code=status.HTTP_204_NO_CONTENT)
def validate_recovery_code(payload: ValidateRecoveryCodeRequest, request: Request) -> None:
    _check_rate_limit(request, _settings(request).password_recovery_ip_rate_limit, "password-recovery-ip", _client_ip(request))
    if get_available_recovery_code(_databases(request).open_registry, payload.recovery_code, int(time.time())) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recovery code not available")


@router.post("/recovery", status_code=status.HTTP_204_NO_CONTENT)
def recover_password(payload: ResetPasswordRequest, request: Request, response: Response) -> None:
    _check_rate_limit(request, _settings(request).password_recovery_ip_rate_limit, "password-recovery-ip", _client_ip(request))
    timestamp = int(time.time())
    if get_available_recovery_code(_databases(request).open_registry, payload.recovery_code, timestamp) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recovery code not available")
    semaphore = request.app.state.password_hash_semaphore
    if not semaphore.acquire(blocking=False):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Password hashing capacity exhausted", headers={"Retry-After": "1"})
    try:
        reset_password(
            _databases(request).open_registry,
            _password_hasher(request),
            payload.recovery_code,
            payload.new_password,
            timestamp,
        )
    except RecoveryCodeNotAvailableError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recovery code not available") from error
    finally:
        semaphore.release()
    clear_authentication_cookies(response)


def _check_rate_limit(request: Request, rate: str, namespace: str, key: str) -> None:
    try:
        _rate_limiter(request).check(rate, namespace, key)
    except RateLimitExceededError as error:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded", headers={"Retry-After": str(error.retry_after)}) from error


def _client_ip(request: Request) -> str:
    return "unknown" if request.client is None else request.client.host


def _databases(request: Request) -> SqliteDatabases:
    return request.app.state.databases


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _password_hasher(request: Request) -> PasswordHasher:
    return request.app.state.password_hasher


def _rate_limiter(request: Request) -> RateLimiter:
    return request.app.state.rate_limiter


def _totp_authenticator(request: Request):
    return request.app.state.totp_authenticator
