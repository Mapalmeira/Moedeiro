import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.authentication import clear_authentication_cookies, require_authenticated_user
from app.api.schema.totp import ConfirmTotpRequest, DisableTotpRequest, StartTotpSetupRequest, StartTotpSetupResponse
from app.application.registry.exceptions import InvalidCurrentPasswordError, InvalidTotpCodeError, InvalidTotpSetupError, TotpAlreadyEnabledError, TotpNotEnabledError
from app.application.registry.use_cases.totp import confirm_totp_setup, disable_totp, start_totp_setup
from app.domain.registry.model.user import User
from app.infrastructure.persistence.sqlite.databases import SqliteDatabases
from app.infrastructure.security.rate_limiter import RateLimitExceededError, RateLimiter
from app.settings import Settings


router = APIRouter(prefix="/api/totp", tags=["totp"])


@router.post("/setup", response_model=StartTotpSetupResponse)
def start_setup(payload: StartTotpSetupRequest, request: Request, user: Annotated[User, Depends(require_authenticated_user)]) -> StartTotpSetupResponse:
    _check_rate_limit(request, _settings(request).totp_setup_ip_attempts_rate_limit, "totp-setup-ip-attempts", _client_ip(request))
    semaphore = request.app.state.password_hash_semaphore
    if not semaphore.acquire(blocking=False):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Password hashing capacity exhausted", headers={"Retry-After": "1"})
    try:
        provisioning_uri = start_totp_setup(
            _databases(request).open_registry,
            request.app.state.password_hasher,
            request.app.state.totp_authenticator,
            user,
            payload.current_password,
            int(time.time()),
        )
    except InvalidCurrentPasswordError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid current password") from error
    except TotpAlreadyEnabledError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="TOTP already enabled") from error
    finally:
        semaphore.release()
    return StartTotpSetupResponse(provisioning_uri=provisioning_uri)


@router.post("/confirm", status_code=status.HTTP_204_NO_CONTENT)
def confirm_setup(payload: ConfirmTotpRequest, request: Request, user: Annotated[User, Depends(require_authenticated_user)]) -> None:
    try:
        confirm_totp_setup(
            _databases(request).open_registry,
            request.app.state.totp_authenticator,
            user,
            payload.code,
            int(time.time()),
        )
    except InvalidTotpSetupError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired TOTP setup") from error
    except InvalidTotpCodeError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code") from error
    except TotpAlreadyEnabledError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="TOTP already enabled") from error


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def remove_totp(payload: DisableTotpRequest, request: Request, response: Response, user: Annotated[User, Depends(require_authenticated_user)]) -> None:
    semaphore = request.app.state.password_hash_semaphore
    if not semaphore.acquire(blocking=False):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Password hashing capacity exhausted", headers={"Retry-After": "1"})
    try:
        disable_totp(
            _databases(request).open_registry,
            request.app.state.password_hasher,
            request.app.state.totp_authenticator,
            user,
            payload.current_password,
            payload.code,
            int(time.time()),
        )
    except (InvalidCurrentPasswordError, InvalidTotpCodeError) as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials") from error
    except TotpNotEnabledError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="TOTP not enabled") from error
    finally:
        semaphore.release()
    clear_authentication_cookies(response)


def _databases(request: Request) -> SqliteDatabases:
    return request.app.state.databases


def _check_rate_limit(request: Request, rate: str, namespace: str, key: str) -> None:
    try:
        _rate_limiter(request).check(rate, namespace, key)
    except RateLimitExceededError as error:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded", headers={"Retry-After": str(error.retry_after)}) from error


def _client_ip(request: Request) -> str:
    return "unknown" if request.client is None else request.client.host


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _rate_limiter(request: Request) -> RateLimiter:
    return request.app.state.rate_limiter
