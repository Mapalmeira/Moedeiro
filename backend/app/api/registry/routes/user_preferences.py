from fastapi import APIRouter, HTTPException, Request, status

from app.api.dependencies.authentication import AuthenticatedUser
from app.api.registry.schema.user_preferences import UserPreferencesPayload
from app.application.registry.exceptions import UserNotFoundError, UserPreferencesNotFoundError
from app.application.registry.use_cases.user_preferences import get_user_preferences, save_user_preferences


router = APIRouter(prefix="/api/user/preferences", tags=["user preferences"])


@router.get("", response_model=UserPreferencesPayload)
def get_preferences(
    request: Request,
    user: AuthenticatedUser,
) -> UserPreferencesPayload:
    try:
        preferences = get_user_preferences(
            request.app.state.databases.open_registry,
            user.uuid,
        )
    except UserPreferencesNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User preferences not found",
        ) from error

    return UserPreferencesPayload.from_preferences(preferences)

@router.put("", response_model=UserPreferencesPayload)
def save_preferences(payload: UserPreferencesPayload, request: Request, user: AuthenticatedUser) -> UserPreferencesPayload:
    try:
        preferences = save_user_preferences(
            request.app.state.databases.open_registry,
            user.uuid,
            payload.language,
            payload.date_format,
            payload.time_format,
            payload.number_format,
            payload.theme,
            payload.timezone,
        )
    except UserNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session") from error
    return UserPreferencesPayload.from_preferences(preferences)
