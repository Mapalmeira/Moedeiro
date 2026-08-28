from uuid import UUID

from pydantic import BaseModel, Field


class LedgerMetadata(BaseModel):
    ledger_uuid: UUID
    name: str = Field(min_length=1, max_length=30)
    schema_version: int = Field(ge=1)
    created_at: int
