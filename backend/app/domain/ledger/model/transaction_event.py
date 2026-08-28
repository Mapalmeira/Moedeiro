from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


TransactionEventType = Literal[
    "TRANSACTION",
    "ACCOUNT_TRANSFER",
    "SHOPPING_LIST",
]


class TransactionEvent(BaseModel):
    uuid: UUID
    occurred_at: int
    description: str = Field(min_length=1, max_length=300)
    type: TransactionEventType
