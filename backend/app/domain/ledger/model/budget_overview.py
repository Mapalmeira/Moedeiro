from typing import Literal

from pydantic import BaseModel

from app.domain.ledger.model.budget import Budget


BudgetOverviewState = Literal["FUTURE", "ACTIVE", "FINISHED"]


class BudgetOverviewItem(BaseModel):
    budget: Budget
    state: BudgetOverviewState
    spent_amount: int | None
    fulfilled: bool | None
