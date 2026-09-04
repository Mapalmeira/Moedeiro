import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response, status

from app.api.dependencies.rate_limit import check_rate_limit
from app.application.registry.exceptions import InvalidSessionError
from app.application.registry.use_cases.authentication import resolve_session_user, update_session_activity
from app.domain.registry.model.remember_session import DEFAULT_EXPIRATION_TIMEOUT_SECONDS
from app.domain.registry.model.user import User


SESSION_COOKIE = "moedeiro_session"
REMEMBER_COOKIE = "moedeiro_remember"
SESSION_COOKIE_PATH = "/api"
REMEMBER_COOKIE_PATH = "/api/authentication"


def require_authenticated_user(request: Request) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    try:
        timestamp = int(time.time())
        session_uuid, user = resolve_session_user(request.app.state.databases.open_registry, token, timestamp)
        check_rate_limit(request, request.app.state.settings.authenticated_user_operations_rate_limit, "authenticated-user-operations", str(user.uuid))
        update_session_activity(request.app.state.databases.open_registry, session_uuid, timestamp)
    except InvalidSessionError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session") from error
    return user


AuthenticatedUser = Annotated[User, Depends(require_authenticated_user)]


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(SESSION_COOKIE, token, path=SESSION_COOKIE_PATH, secure=True, httponly=True, samesite="strict")


def set_remember_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        REMEMBER_COOKIE,
        token,
        max_age=DEFAULT_EXPIRATION_TIMEOUT_SECONDS,
        path=REMEMBER_COOKIE_PATH,
        secure=True,
        httponly=True,
        samesite="strict",
    )


def clear_authentication_cookies(response: Response) -> None:
    _delete_cookie(response, SESSION_COOKIE, SESSION_COOKIE_PATH)
    _delete_cookie(response, REMEMBER_COOKIE, REMEMBER_COOKIE_PATH)


def delete_remember_cookie(response: Response) -> None:
    _delete_cookie(response, REMEMBER_COOKIE, REMEMBER_COOKIE_PATH)


def _delete_cookie(response: Response, name: str, path: str) -> None:
    response.delete_cookie(name, path=path, secure=True, httponly=True, samesite="strict")
