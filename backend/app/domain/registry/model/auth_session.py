from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


DEFAULT_INACTIVITY_TIMEOUT_SECONDS = 30 * 60
DEFAULT_ABSOLUTE_TIMEOUT_SECONDS = 12 * 60 * 60


class AuthSession(BaseModel):
    uuid: UUID
    user_uuid: UUID
    token_hash: bytes
    created_at: int = Field(ge=0)
    expires_at: int = Field(ge=0)
    inactivity_timeout_seconds: int = Field(gt=0)
    last_activity_at: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be greater than created_at")
        if self.last_activity_at is not None and self.last_activity_at < self.created_at:
            raise ValueError("last_activity_at must not precede created_at")
        if self.last_activity_at is not None and self.last_activity_at >= self.expires_at:
            raise ValueError("last_activity_at must precede expires_at")
        return self
