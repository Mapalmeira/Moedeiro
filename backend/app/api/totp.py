import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.authentication import clear_authentication_cookies, require_authenticated_user
from app.api.schema.totp import DisableTotpRequest, EnableTotpRequest, EnableTotpResponse, StartTotpSetupRequest, StartTotpSetupResponse
from app.application.registry.exceptions import InvalidCurrentPasswordError, InvalidTotpCodeError, InvalidTotpSetupError, TotpAlreadyEnabledError, TotpNotEnabledError
from app.application.registry.use_cases.totp import disable_totp, enable_totp, start_totp_setup
from app.domain.registry.model.user import User
from app.infrastructure.persistence.sqlite.databases import SqliteDatabases


router = APIRouter(prefix="/api/totp", tags=["totp"])


@router.post("/setup", response_model=StartTotpSetupResponse)
def start_setup(payload: StartTotpSetupRequest, request: Request, user: Annotated[User, Depends(require_authenticated_user)]) -> StartTotpSetupResponse:
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


@router.post("/enable", response_model=EnableTotpResponse)
def confirm_setup(payload: EnableTotpRequest, request: Request, user: Annotated[User, Depends(require_authenticated_user)]) -> EnableTotpResponse:
    try:
        recovery_codes = enable_totp(
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
    return EnableTotpResponse(recovery_codes=recovery_codes)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def disable(payload: DisableTotpRequest, request: Request, response: Response, user: Annotated[User, Depends(require_authenticated_user)]) -> None:
    try:
        disable_totp(_databases(request).open_registry, request.app.state.totp_authenticator, user, payload.code, int(time.time()))
    except InvalidTotpCodeError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code") from error
    except TotpNotEnabledError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TOTP not enabled") from error
    clear_authentication_cookies(response)


def _databases(request: Request) -> SqliteDatabases:
    return request.app.state.databases
