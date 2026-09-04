from fastapi import APIRouter, HTTPException, Request, status

from app.api.dependencies.authentication import AuthenticatedUser
from app.api.registry.schema.user_preferences import UpdateUserPreferencesRequest, UserPreferencesResponse
from app.application.registry.exceptions import UserNotFoundError
from app.application.registry.use_cases.user_preferences import get_user_preferences, save_user_preferences


router = APIRouter(prefix="/api/user/preferences", tags=["user preferences"])


@router.get("", response_model=UserPreferencesResponse)
def get_preferences(request: Request, user: AuthenticatedUser) -> UserPreferencesResponse:
    preferences = get_user_preferences(request.app.state.databases.open_registry, user.uuid)
    return UserPreferencesResponse.from_preferences(preferences)


@router.put("", response_model=UserPreferencesResponse)
def save_preferences(payload: UpdateUserPreferencesRequest, request: Request, user: AuthenticatedUser) -> UserPreferencesResponse:
    try:
        preferences = save_user_preferences(
            request.app.state.databases.open_registry,
            user.uuid,
            payload.date_format,
            payload.time_format,
            payload.number_format,
            payload.theme,
            payload.timezone,
        )
    except UserNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session") from error
    return UserPreferencesResponse.from_preferences(preferences)
