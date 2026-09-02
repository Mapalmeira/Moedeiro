from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


DEFAULT_EXPIRATION_TIMEOUT_SECONDS = 60 * 60
RecoveryCodeValue = Annotated[str, Field(min_length=16, max_length=16, pattern=r"^[0-9ABCDEFGHJKMNPQRSTVWXYZ]{16}$")]


class RecoveryCode(BaseModel):
    uuid: UUID
    user_uuid: UUID
    code_hash: bytes
    created_at: int = Field(ge=0)
    expires_at: int = Field(ge=0)
    used_at: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be greater than created_at")
        if self.used_at is not None and self.used_at < self.created_at:
            raise ValueError("used_at must not precede created_at")
        if self.used_at is not None and self.used_at >= self.expires_at:
            raise ValueError("used_at must precede expires_at")
        return self
