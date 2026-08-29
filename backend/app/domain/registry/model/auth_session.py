from uuid import UUID

from pydantic import BaseModel, Field, model_validator


DEFAULT_INACTIVITY_TIMEOUT_SECONDS = 30 * 60
DEFAULT_ABSOLUTE_TIMEOUT_SECONDS = 12 * 60 * 60


class AuthSession(BaseModel):
    uuid: UUID
    grant_uuid: UUID
    token_hash: bytes = Field(min_length=32, max_length=32)
    created_at: int = Field(ge=0)
    inactivity_timeout_seconds: int = Field(default=DEFAULT_INACTIVITY_TIMEOUT_SECONDS, gt=0)
    absolute_timeout_seconds: int = Field(default=DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, gt=0)
    last_activity_at: int | None = Field(default=None, ge=0)
    revoked_at: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_state(self) -> "AuthSession":
        if self.inactivity_timeout_seconds > self.absolute_timeout_seconds:
            raise ValueError("inactivity timeout must not exceed absolute timeout")
        if self.last_activity_at is not None and self.last_activity_at < self.created_at:
            raise ValueError("last_activity_at must not precede created_at")
        if self.last_activity_at is not None and self.last_activity_at >= self.created_at + self.absolute_timeout_seconds:
            raise ValueError("last_activity_at must precede the absolute timeout")
        if self.revoked_at is not None and self.revoked_at < self.created_at:
            raise ValueError("revoked_at must not precede created_at")
        return self
