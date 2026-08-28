from uuid import UUID
from pydantic import BaseModel, Field

class LedgerToken(BaseModel):
    uuid: UUID
    ledger_uuid: UUID
    token_hash: str = Field(min_length=1, max_length=255)
    label: str | None = Field(default=None, max_length=30)
    created_at: int
    revoked_at: int | None = None
