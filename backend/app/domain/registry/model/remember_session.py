from uuid import UUID

from pydantic import BaseModel, Field, model_validator


DEFAULT_EXPIRATION_TIMEOUT_SECONDS = 30 * 24 * 60 * 60
class RememberSession(BaseModel):
    uuid: UUID
    user_uuid: UUID
    token_hash: bytes
    created_at: int = Field(ge=0)
    expiration_timeout_seconds: int = Field(default=DEFAULT_EXPIRATION_TIMEOUT_SECONDS, gt=0)
    last_used_at: int | None = Field(default=None, ge=0)
    revoked_at: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_state(self) -> "RememberSession":
        if self.last_used_at is not None and self.last_used_at < self.created_at:
            raise ValueError("last_used_at must not precede created_at")
        if self.last_used_at is not None and self.last_used_at >= self.created_at + self.expiration_timeout_seconds:
            raise ValueError("last_used_at must precede expiration")
        if self.revoked_at is not None and self.revoked_at < self.created_at:
            raise ValueError("revoked_at must not precede created_at")
        return self
