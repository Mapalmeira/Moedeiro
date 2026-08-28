from uuid import UUID

from pydantic import BaseModel, Field


class BudgetStatus(BaseModel):
    budget_uuid: UUID
    budgeted_amount: int = Field(ge=0)
    spent_amount: int = Field(ge=0)
    over_budget: bool
