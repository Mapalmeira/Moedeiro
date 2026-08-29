from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class AccessInvitation(BaseModel):
    uuid: UUID
    ledger_uuid: UUID
    grant_uuid: UUID
    secret_hash: bytes = Field(min_length=32, max_length=32)
    created_at: int = Field(ge=0)
    expires_at: int = Field(ge=0)
    consumed_at: int | None = Field(default=None, ge=0)
    revoked_at: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_state(self) -> "AccessInvitation":
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be greater than created_at")
        if self.consumed_at is not None and self.consumed_at < self.created_at:
            raise ValueError("consumed_at must not precede created_at")
        if self.consumed_at is not None and self.consumed_at >= self.expires_at:
            raise ValueError("consumed_at must precede expires_at")
        if self.revoked_at is not None and self.revoked_at < self.created_at:
            raise ValueError("revoked_at must not precede created_at")
        if self.consumed_at is not None and self.revoked_at is not None:
            raise ValueError("an invitation cannot be both consumed and revoked")
        return self
