import time

from fastapi import APIRouter, HTTPException, Request, status

from app.api.schema.registration import RegisterUserRequest
from app.api.credential_operation import execute_credential_operation
from app.application.registry.exceptions import InvitationNotAvailableError, UserNameUnavailableError
from app.application.registry.password_hasher import PasswordHasher
from app.application.registry.use_cases.register_user import register_user
from app.application.registry.use_cases.user_invitation import get_available_user_invitation
from app.infrastructure.persistence.sqlite.databases import SqliteDatabases
from app.infrastructure.security.rate_limiter import RateLimitExceededError, RateLimiter
from app.settings import Settings


router = APIRouter(prefix="/api/registration", tags=["registration"])


@router.post("", status_code=status.HTTP_204_NO_CONTENT)
async def create_user(payload: RegisterUserRequest, request: Request) -> None:
    _check_rate_limit(request, _settings(request).registration_ip_attempts_rate_limit, "registration-ip-attempts", _client_ip(request))
    timestamp = int(time.time())

    def operation() -> None:
        invitation = get_available_user_invitation(_databases(request).open_registry, payload.invitation_code, timestamp)
        if invitation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not available")
        register_user(
            _databases(request).open_registry,
            _password_hasher(request),
            invitation.uuid,
            payload.name,
            payload.password,
            timestamp,
        )

    try:
        await execute_credential_operation(request, operation)
    except InvitationNotAvailableError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not available") from error
    except UserNameUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User name not available") from error


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
