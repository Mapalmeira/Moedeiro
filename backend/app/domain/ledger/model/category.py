from uuid import UUID

from pydantic import BaseModel, Field


class Category(BaseModel):
    uuid: UUID
    name: str = Field(min_length=1, max_length=30)
    parent_uuid: UUID | None = None
