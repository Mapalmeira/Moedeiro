from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


WebAuthnCredentialName = Annotated[str, Field(min_length=1, max_length=50)]


class WebAuthnCredential(BaseModel):
    uuid: UUID
    user_uuid: UUID
    credential_id: bytes
    public_key: bytes
    sign_count: int = Field(ge=0)
    created_at: int = Field(ge=0)
    last_used_at: int | None = Field(default=None, ge=0)
    name: WebAuthnCredentialName

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.last_used_at is not None and self.last_used_at < self.created_at:
            raise ValueError("last_used_at must not precede created_at")
        return self
