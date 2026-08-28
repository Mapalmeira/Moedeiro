from uuid import UUID
from pydantic import BaseModel, Field

class Account(BaseModel):
    uuid: UUID
    name: str = Field(min_length=1, max_length=30)
    note: str | None = Field(default=None, max_length=300)
    currency_uuid: UUID
