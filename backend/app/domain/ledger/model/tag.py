from uuid import UUID

from pydantic import BaseModel, Field


class Tag(BaseModel):
    uuid: UUID
    name: str = Field(min_length=1, max_length=30)
