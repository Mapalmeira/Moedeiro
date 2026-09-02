import time
from functools import partial
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.authentication import clear_authentication_cookies, require_authenticated_user
from app.api.credential_operation import execute_credential_operation
from app.api.schema.password import ChangePasswordRequest, ResetPasswordRequest
from app.application.registry.exceptions import InvalidCurrentPasswordError, InvalidTotpCodeError, PasswordUpdateConflictError, RecoveryCodeNotAvailableError, TotpRequiredError, UserNotFoundError
from app.application.registry.password_hasher import PasswordHasher
from app.application.registry.use_cases.password import change_password, recover_password as recover_password_use_case
from app.domain.registry.model.user import User
from app.infrastructure.persistence.sqlite.databases import SqliteDatabases
from app.infrastructure.security.rate_limiter import RateLimitExceededError, RateLimiter
from app.settings import Settings


router = APIRouter(prefix="/api/password", tags=["password"])


@router.post("/change", status_code=status.HTTP_204_NO_CONTENT)
async def change_current_password(payload: ChangePasswordRequest, request: Request, user: Annotated[User, Depends(require_authenticated_user)]) -> None:
    try:
        await execute_credential_operation(
            request,
            partial(
                change_password,
                _databases(request).open_registry,
                _password_hasher(request),
                user,
                payload.current_password,
                payload.new_password,
                int(time.time()),
                _totp_authenticator(request),
                payload.totp_code,
            ),
        )
    except TotpRequiredError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="TOTP required") from error
    except InvalidTotpCodeError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code") from error
    except InvalidCurrentPasswordError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid current password") from error
    except UserNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session") from error
    except PasswordUpdateConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Password update conflict") from error
@router.post("/recovery", status_code=status.HTTP_204_NO_CONTENT)
async def recover_password(payload: ResetPasswordRequest, request: Request, response: Response) -> None:
    _check_rate_limit(request, _settings(request).password_recovery_ip_attempts_rate_limit, "password-recovery-ip-attempts", _client_ip(request))
    timestamp = int(time.time())
    try:
        await execute_credential_operation(
            request,
            partial(
                recover_password_use_case,
                _databases(request).open_registry,
                _password_hasher(request),
                _totp_authenticator(request),
                payload.name,
                payload.recovery_code,
                payload.new_password,
                payload.totp_code,
                timestamp,
            ),
        )
    except TotpRequiredError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="TOTP required") from error
    except InvalidTotpCodeError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code") from error
    except (UserNotFoundError, RecoveryCodeNotAvailableError) as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials") from error
    except PasswordUpdateConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Password update conflict") from error
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
