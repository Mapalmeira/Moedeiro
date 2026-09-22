from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self

from app.domain.registry.model.ledger_grant import LedgerGrant


class LedgerTokenGrant(BaseModel):
    grant: LedgerGrant
    name: str = Field(min_length=1, max_length=50)
    token_hash: bytes = Field(min_length=32, max_length=32)

    @model_validator(mode="after")
    def validate_grant_type(self) -> Self:
        if self.grant.type != "EXTERNAL_ACCESS":
            raise ValueError("token grant requires an EXTERNAL_ACCESS grant")
        return self
