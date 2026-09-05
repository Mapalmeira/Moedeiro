import time
from functools import partial
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies.authentication import require_authenticated_user
from app.api.dependencies.credential_operation import execute_credential_operation
from app.api.dependencies.rate_limit import check_rate_limit
from app.api.registry.schema.totp import ConfirmTotpRequest, DisableTotpRequest, StartTotpSetupRequest, StartTotpSetupResponse, TotpStatusResponse
from app.application.registry.exceptions import InvalidCurrentPasswordError, InvalidTotpCodeError, InvalidTotpSetupError, TotpAlreadyEnabledError, TotpNotEnabledError
from app.application.registry.use_cases.totp import confirm_totp_setup, disable_totp, is_totp_enabled, start_totp_setup
from app.domain.registry.model.user import User
from app.infrastructure.persistence.sqlite.databases import SqliteDatabases
from app.settings import Settings


router = APIRouter(prefix="/api/totp", tags=["totp"])


@router.get("", response_model=TotpStatusResponse)
def get_totp_status(request: Request, user: Annotated[User, Depends(require_authenticated_user)]) -> TotpStatusResponse:
    enabled = is_totp_enabled(_databases(request).open_registry, user.uuid)
    return TotpStatusResponse(enabled=enabled)


@router.post("/setup", response_model=StartTotpSetupResponse)
async def start_setup(payload: StartTotpSetupRequest, request: Request, user: Annotated[User, Depends(require_authenticated_user)]) -> StartTotpSetupResponse:
    check_rate_limit(request, _settings(request).totp_setup_ip_attempts_rate_limit, "totp-setup-ip-attempts")
    try:
        provisioning_uri = await execute_credential_operation(
            request,
            partial(
                start_totp_setup,
                _databases(request).open_registry,
                request.app.state.password_hasher,
                request.app.state.totp_authenticator,
                user,
                payload.current_password,
                int(time.time()),
            ),
        )
    except InvalidCurrentPasswordError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid current password") from error
    except TotpAlreadyEnabledError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="TOTP already enabled") from error
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
    except (InvalidCurrentPasswordError, InvalidTotpCodeError) as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials") from error
    except TotpNotEnabledError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="TOTP not enabled") from error


def _databases(request: Request) -> SqliteDatabases:
    return request.app.state.databases


def _settings(request: Request) -> Settings:
    return request.app.state.settings
