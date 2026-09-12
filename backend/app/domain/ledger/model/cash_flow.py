from uuid import UUID

from pydantic import BaseModel, Field


class CashFlow(BaseModel):
    """Economic cash movement for the interval supplied to its query.

    * income and expense contain incoming and outgoing amounts respectively.
    * event_count counts the matching events represented by the result
    * income_movement_count and expense_movement_count count the movements included in each amount.

    Every amount belongs to currency_uuid. ACCOUNT_TRANSFER events are excluded
    from ledger-wide results, but their movement for a selected account is
    included when account_uuid is part of the query filter.
    """

    currency_uuid: UUID
    income: int = Field(ge=0)
    expense: int = Field(ge=0)
    event_count: int = Field(ge=0)
    income_movement_count: int = Field(ge=0)
    expense_movement_count: int = Field(ge=0)
