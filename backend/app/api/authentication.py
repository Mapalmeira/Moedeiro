import time

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api.schema.authentication import LoginRequest
from app.application.registry.exceptions import InvalidCredentialsError, InvalidSessionError
from app.application.registry.password_hasher import PasswordHasher
from app.application.registry.use_cases.authentication import authenticate_session, login, logout, refresh_session
from app.domain.registry.model.remember_session import DEFAULT_EXPIRATION_TIMEOUT_SECONDS
from app.domain.registry.model.user import User
from app.infrastructure.persistence.sqlite.databases import SqliteDatabases
from app.infrastructure.security.rate_limiter import RateLimitExceededError, RateLimiter
from app.settings import Settings


router = APIRouter(prefix="/api/authentication", tags=["authentication"])

_SESSION_COOKIE = "moedeiro_session"
_REMEMBER_COOKIE = "moedeiro_remember"
_SESSION_COOKIE_PATH = "/api"
_REMEMBER_COOKIE_PATH = "/api/authentication"


@router.post("/login", status_code=status.HTTP_204_NO_CONTENT)
def login_user(payload: LoginRequest, request: Request, response: Response) -> None:
    _check_rate_limit(request, _settings(request).login_ip_rate_limit, "login-ip", _client_ip(request))
    semaphore = request.app.state.password_hash_semaphore

    if not semaphore.acquire(blocking=False):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Password hashing capacity exhausted", headers={"Retry-After": "1"})
    try:
        session_token, remember_token = login(
            _databases(request).open_registry,
            _password_hasher(request),
            payload.name,
            payload.password,
            payload.remember,
            int(time.time()),
            request.cookies.get(_SESSION_COOKIE),
            request.cookies.get(_REMEMBER_COOKIE),
        )
    except InvalidCredentialsError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials") from error
    finally:
        semaphore.release()

    _set_session_cookie(response, session_token)
    if remember_token is None:
        _delete_cookie(response, _REMEMBER_COOKIE, _REMEMBER_COOKIE_PATH)
    else:
        _set_remember_cookie(response, remember_token)


@router.get("/session", status_code=status.HTTP_204_NO_CONTENT)
def validate_session(request: Request) -> None:
    require_authenticated_user(request)


@router.post("/refresh", status_code=status.HTTP_204_NO_CONTENT)
def refresh(request: Request, response: Response) -> None:
    token = request.cookies.get(_REMEMBER_COOKIE)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    try:
        session_token, remember_token = refresh_session(_databases(request).open_registry, token, int(time.time()))
    except InvalidSessionError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session") from error
    _set_session_cookie(response, session_token)
    _set_remember_cookie(response, remember_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_user(request: Request, response: Response) -> None:
    logout(
        _databases(request).open_registry,
        request.cookies.get(_SESSION_COOKIE),
        request.cookies.get(_REMEMBER_COOKIE),
        int(time.time()),
    )
    clear_authentication_cookies(response)


def require_authenticated_user(request: Request) -> User:
    token = request.cookies.get(_SESSION_COOKIE)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    try:
        return authenticate_session(_databases(request).open_registry, token, int(time.time()))
    except InvalidSessionError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session") from error


def clear_authentication_cookies(response: Response) -> None:
    _delete_cookie(response, _SESSION_COOKIE, _SESSION_COOKIE_PATH)
    _delete_cookie(response, _REMEMBER_COOKIE, _REMEMBER_COOKIE_PATH)


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(_SESSION_COOKIE, token, path=_SESSION_COOKIE_PATH, secure=True, httponly=True, samesite="strict")


def _set_remember_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        _REMEMBER_COOKIE,
        token,
        max_age=DEFAULT_EXPIRATION_TIMEOUT_SECONDS,
        path=_REMEMBER_COOKIE_PATH,
        secure=True,
        httponly=True,
        samesite="strict",
    )


def _delete_cookie(response: Response, name: str, path: str) -> None:
    response.delete_cookie(name, path=path, secure=True, httponly=True, samesite="strict")


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
