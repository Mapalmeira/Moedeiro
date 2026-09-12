from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self


MfaMethodType = Literal["TOTP"]
TOTP_SETUP_TTL_SECONDS = 10 * 60


def totp_setup_expires_at(created_at: int) -> int:
    return created_at + TOTP_SETUP_TTL_SECONDS


class MfaMethod(BaseModel):
    uuid: UUID
    user_uuid: UUID
    type: MfaMethodType
    secret_encrypted: bytes
    created_at: int = Field(ge=0)
    expires_unconfirmed_at: int = Field(ge=0)
    confirmed_at: int | None = Field(default=None, ge=0)
    last_used_counter: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.expires_unconfirmed_at <= self.created_at:
            raise ValueError("expires_unconfirmed_at must be greater than created_at")
        if self.confirmed_at is not None and self.confirmed_at < self.created_at:
            raise ValueError("confirmed_at must not precede created_at")
        return self
