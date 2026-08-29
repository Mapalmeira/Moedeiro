from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.domain.ledger.model.financial_event import FinancialEventType


class FinancialEventFilter(BaseModel):
    """Filtering criteria shared by transaction-event queries.

    Different criteria are combined with AND. Within category_uuids, tag_uuids
    and event_types, matching any value is sufficient.
    
    The required time interval is half-open: from_timestamp is inclusive and
    to_timestamp is exclusive.
    """

    from_timestamp: int
    to_timestamp: int
    account_uuid: UUID | None = None
    category_uuids: set[UUID] = Field(default_factory=set)
    tag_uuids: set[UUID] = Field(default_factory=set)
    event_types: set[FinancialEventType] = Field(default_factory=set)

    @model_validator(mode="after")
    def validate_period(self) -> "FinancialEventFilter":
        if self.from_timestamp >= self.to_timestamp:
            raise ValueError("from_timestamp must be less than to_timestamp")
        return self
