from uuid import UUID

from pydantic import BaseModel, Field, model_validator


DEFAULT_EXPIRATION_TIMEOUT_SECONDS = 60 * 60


class UserInvitation(BaseModel):
    uuid: UUID
    secret_hash: bytes
    created_at: int = Field(ge=0)
    expiration_timeout_seconds: int = Field(default=DEFAULT_EXPIRATION_TIMEOUT_SECONDS, gt=0)
    consumed_at: int | None = Field(default=None, ge=0)
    revoked_at: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_state(self) -> "UserInvitation":
        if self.consumed_at is not None and self.consumed_at < self.created_at:
            raise ValueError("consumed_at must not precede created_at")
        if self.consumed_at is not None and self.consumed_at >= self.created_at + self.expiration_timeout_seconds:
            raise ValueError("consumed_at must precede the expiration timeout")
        if self.revoked_at is not None and self.revoked_at < self.created_at:
            raise ValueError("revoked_at must not precede created_at")
        if self.consumed_at is not None and self.revoked_at is not None:
            raise ValueError("an invitation cannot be both consumed and revoked")
        return self
