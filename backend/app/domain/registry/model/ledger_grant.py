from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


LedgerRole = Literal["OWNER", "EDITOR", "READER"]


class LedgerGrant(BaseModel):
    uuid: UUID
    user_uuid: UUID
    ledger_uuid: UUID
    role: LedgerRole
    created_at: int = Field(ge=0)
    revoked_at: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.revoked_at is not None and self.revoked_at < self.created_at:
            raise ValueError("revoked_at must not precede created_at")
        return self
