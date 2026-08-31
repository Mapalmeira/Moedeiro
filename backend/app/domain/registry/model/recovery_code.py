from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class RecoveryCode(BaseModel):
    uuid: UUID
    user_uuid: UUID
    code_hash: bytes
    created_at: int = Field(ge=0)
    used_at: int | None = Field(default=None, ge=0)
    revoked_at: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.used_at is not None and self.used_at < self.created_at:
            raise ValueError("used_at must not precede created_at")
        if self.revoked_at is not None and self.revoked_at < self.created_at:
            raise ValueError("revoked_at must not precede created_at")
        if self.used_at is not None and self.revoked_at is not None:
            raise ValueError("used_at and revoked_at are mutually exclusive")
        return self
