import time
from functools import partial
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.dependencies.authentication import require_authenticated_user
from app.api.dependencies.credential_operation import execute_credential_operation
from app.api.dependencies.rate_limit import check_rate_limit
from app.api.registry.schema.totp import ConfirmTotpRequest, DisableTotpRequest, StartTotpSetupRequest
from app.application.registry.exceptions import InvalidCurrentPasswordError, InvalidTotpCodeError, InvalidTotpSetupError, TotpAlreadyEnabledError, TotpCodeAlreadyUsedError, TotpNotEnabledError
from app.application.registry.use_cases.totp import confirm_totp_setup, disable_totp, get_totp_status, start_totp_setup
from app.domain.registry.model.totp import TotpStatus
from app.domain.registry.model.user import User
from app.infrastructure.persistence.sqlite.databases import SqliteDatabases
from app.settings import Settings


router = APIRouter(prefix="/api/totp", tags=["totp"])


@router.get("", response_model=TotpStatus)
def get_status(response: Response, request: Request, user: Annotated[User, Depends(require_authenticated_user)]) -> TotpStatus:
    totp_status = get_totp_status(
        _databases(request).open_registry,
        request.app.state.totp_authenticator,
        user,
        int(time.time()),
    )
    if totp_status.state == "PENDING":
        response.headers["Cache-Control"] = "no-store"
    return totp_status


@router.post("/setup", response_model=TotpStatus)
async def start_setup(payload: StartTotpSetupRequest, request: Request, user: Annotated[User, Depends(require_authenticated_user)]) -> TotpStatus:
    check_rate_limit(request, _settings(request).totp_setup_ip_attempts_rate_limit, "totp-setup-ip-attempts")
    timestamp = int(time.time())
    try:
        totp_status = await execute_credential_operation(
            request,
            partial(
                start_totp_setup,
                _databases(request).open_registry,
                request.app.state.password_hasher,
                request.app.state.totp_authenticator,
                user,
                payload.current_password,
                timestamp,
            ),
        )
    except InvalidCurrentPasswordError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid current password") from error
    except TotpAlreadyEnabledError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="TOTP already enabled") from error
    return totp_status


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
async def remove_totp(payload: DisableTotpRequest, request: Request, user: Annotated[User, Depends(require_authenticated_user)]) -> None:
    try:
        await execute_credential_operation(
            request,
            partial(
                disable_totp,
                _databases(request).open_registry,
                request.app.state.password_hasher,
                request.app.state.totp_authenticator,
                user,
                payload.current_password,
                payload.code,
                int(time.time()),
            ),
        )
    except TotpCodeAlreadyUsedError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="TOTP code already used") from error
    except InvalidCurrentPasswordError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid current password") from error
    except InvalidTotpCodeError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code") from error
    except TotpNotEnabledError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="TOTP not enabled") from error


def _databases(request: Request) -> SqliteDatabases:
    return request.app.state.databases


def _settings(request: Request) -> Settings:
    return request.app.state.settings
