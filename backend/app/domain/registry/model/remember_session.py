from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self


DEFAULT_EXPIRATION_TIMEOUT_SECONDS = 30 * 24 * 60 * 60


class RememberSession(BaseModel):
    uuid: UUID
    user_uuid: UUID
    token_hash: bytes
    created_at: int = Field(ge=0)
    expires_at: int = Field(ge=0)
    last_used_at: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be greater than created_at")
        if self.last_used_at is not None and self.last_used_at < self.created_at:
            raise ValueError("last_used_at must not precede created_at")
        if self.last_used_at is not None and self.last_used_at >= self.expires_at:
            raise ValueError("last_used_at must precede expires_at")
        return self
