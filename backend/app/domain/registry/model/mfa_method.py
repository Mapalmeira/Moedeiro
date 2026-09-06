from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


MfaMethodType = Literal["TOTP"]
TOTP_SETUP_TTL_SECONDS = 10 * 60


class MfaMethod(BaseModel):
    uuid: UUID
    user_uuid: UUID
    type: MfaMethodType
    secret_encrypted: bytes
    created_at: int = Field(ge=0)
    confirmed_at: int | None = Field(default=None, ge=0)
    last_used_counter: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.confirmed_at is not None and self.confirmed_at < self.created_at:
            raise ValueError("confirmed_at must not precede created_at")
        return self
