from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.domain.registry.model.crockford_code import CrockfordCode


DEFAULT_EXPIRATION_TIMEOUT_SECONDS = 60 * 60
InvitationCode = CrockfordCode


class UserInvitation(BaseModel):
    uuid: UUID
    secret_hash: bytes
    created_at: int = Field(ge=0)
    expires_at: int = Field(ge=0)
    consumed_at: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be greater than created_at")
        if self.consumed_at is not None and self.consumed_at < self.created_at:
            raise ValueError("consumed_at must not precede created_at")
        if self.consumed_at is not None and self.consumed_at >= self.expires_at:
            raise ValueError("consumed_at must precede expires_at")
        return self
