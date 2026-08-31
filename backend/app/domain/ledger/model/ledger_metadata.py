from uuid import UUID

from pydantic import BaseModel, Field


class LedgerMetadata(BaseModel):
    ledger_uuid: UUID
    schema_version: int = Field(ge=1)
    revision: int = Field(ge=0)
    created_at: int = Field(ge=0)
