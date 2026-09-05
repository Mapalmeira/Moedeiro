import time
from functools import partial

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api.dependencies.authentication import REMEMBER_COOKIE, SESSION_COOKIE, clear_authentication_cookies, delete_remember_cookie, require_authenticated_user, set_remember_cookie, set_session_cookie
from app.api.dependencies.credential_operation import execute_credential_operation
from app.api.dependencies.rate_limit import check_rate_limit
from app.api.registry.schema.authentication import LoginRequest
from app.application.registry.exceptions import InvalidCredentialsError, InvalidSessionError, InvalidTotpCodeError, TotpCodeAlreadyUsedError, TotpRequiredError, UserNotFoundError
from app.application.registry.password_hasher import PasswordHasher
from app.application.registry.use_cases.authentication import login, logout, refresh_session
from app.infrastructure.persistence.sqlite.databases import SqliteDatabases
from app.settings import Settings


router = APIRouter(prefix="/api/authentication", tags=["authentication"])


@router.post("/login", status_code=status.HTTP_204_NO_CONTENT)
async def login_user(payload: LoginRequest, request: Request, response: Response) -> None:
    check_rate_limit(request, _settings(request).login_ip_attempts_rate_limit, "login-ip-attempts")
    try:
        session_token, remember_token = await execute_credential_operation(
            request,
            partial(
                login,
                _databases(request).open_registry,
                _password_hasher(request),
                payload.name,
                payload.password,
                payload.remember,
                int(time.time()),
                request.cookies.get(SESSION_COOKIE),
                request.cookies.get(REMEMBER_COOKIE),
                _totp_authenticator(request),
                payload.totp_code,
            ),
        )
    except TotpRequiredError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="TOTP required") from error
    except TotpCodeAlreadyUsedError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="TOTP code already used") from error
    except (UserNotFoundError, InvalidTotpCodeError, InvalidCredentialsError) as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials") from error
    secure = not _settings(request).allow_insecure_http
    set_session_cookie(response, session_token, secure)
    if remember_token is None:
        delete_remember_cookie(response, secure)
    else:
        set_remember_cookie(response, remember_token, secure)


@router.get("/session", status_code=status.HTTP_204_NO_CONTENT)
def validate_session(request: Request) -> None:
    require_authenticated_user(request)


@router.post("/refresh", status_code=status.HTTP_204_NO_CONTENT)
def refresh(request: Request, response: Response) -> None:
    check_rate_limit(request, _settings(request).refresh_ip_attempts_rate_limit, "refresh-ip-attempts")
    token = request.cookies.get(REMEMBER_COOKIE)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    try:
        session_token, remember_token = refresh_session(_databases(request).open_registry, token, int(time.time()))
    except InvalidSessionError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session") from error
    secure = not _settings(request).allow_insecure_http
    set_session_cookie(response, session_token, secure)
    set_remember_cookie(response, remember_token, secure)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_user(request: Request, response: Response) -> None:
    logout(
        _databases(request).open_registry,
        request.cookies.get(SESSION_COOKIE),
        request.cookies.get(REMEMBER_COOKIE),
    )
    clear_authentication_cookies(response, not _settings(request).allow_insecure_http)


def _databases(request: Request) -> SqliteDatabases:
    return request.app.state.databases


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _password_hasher(request: Request) -> PasswordHasher:
    return request.app.state.password_hasher


def _totp_authenticator(request: Request):
    return request.app.state.totp_authenticator
