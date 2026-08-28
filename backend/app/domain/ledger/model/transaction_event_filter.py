from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.domain.ledger.model.transaction_event import TransactionEventType


class TransactionEventFilter(BaseModel):
    from_timestamp: int | None = None
    to_timestamp: int | None = None
    account_uuid: UUID | None = None
    category_uuids: set[UUID] = Field(default_factory=set)
    tag_uuids: set[UUID] = Field(default_factory=set)
    event_types: set[TransactionEventType] = Field(default_factory=set)

    @model_validator(mode="after")
    def validate_period(self) -> "TransactionEventFilter":
        if (
            self.from_timestamp is not None
            and self.to_timestamp is not None
            and self.from_timestamp >= self.to_timestamp
        ):
            raise ValueError("from_timestamp must be less than to_timestamp")
        return self
