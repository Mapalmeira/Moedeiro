from uuid import UUID
from pydantic import BaseModel, Field

class Ledger(BaseModel):
    uuid: UUID
    path: str = Field(min_length=1)
