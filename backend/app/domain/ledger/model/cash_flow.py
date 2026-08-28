from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class CashFlow(BaseModel):
    """Economic cash movement for a represented interval.

    * income and expense contain incoming and outgoing amounts respectively.
    * event_count counts the matching events represented by the result
    * income_movement_count and expense_movement_count count the movements included in each amount.

    Every amount belongs to currency_uuid. ACCOUNT_TRANSFER events and their
    movements are excluded from every value.
    """

    currency_uuid: UUID
    from_timestamp: int
    to_timestamp: int
    income: int = Field(ge=0)
    expense: int = Field(ge=0)
    event_count: int = Field(ge=0)
    income_movement_count: int = Field(ge=0)
    expense_movement_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_period(self) -> "CashFlow":
        if self.from_timestamp > self.to_timestamp:
            raise ValueError("from_timestamp must be less than or equal to to_timestamp")
        return self
