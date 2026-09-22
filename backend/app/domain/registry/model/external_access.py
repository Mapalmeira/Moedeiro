from uuid import UUID

from pydantic import BaseModel, Field


class ExternalAccess(BaseModel):
    uuid: UUID
    user_uuid: UUID
    name: str = Field(min_length=1, max_length=50)
    token_hash: bytes = Field(min_length=32, max_length=32)
