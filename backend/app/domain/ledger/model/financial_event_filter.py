from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.domain.ledger.model.financial_event import FinancialEventType


class FinancialEventFilter(BaseModel):
    """Filtering criteria shared by financial-event queries.

    Different criteria are combined with AND.

    The required time interval is half-open: from_timestamp is inclusive and
    to_timestamp is exclusive.
    """

    model_config = ConfigDict(extra="forbid")

    from_timestamp: int
    to_timestamp: int
    account_uuid: UUID | None = None
    category_uuid: UUID | None = None
    event_type: FinancialEventType | None = None

    @model_validator(mode="after")
    def validate_period(self) -> Self:
        if self.from_timestamp >= self.to_timestamp:
            raise ValueError("from_timestamp must be less than to_timestamp")
        return self
