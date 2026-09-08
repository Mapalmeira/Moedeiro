from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.domain.appearance import Icon
from app.domain.ledger.model.budget import Budget, BudgetAmount, BudgetDescription, BudgetName
from app.domain.ledger.model.budget_overview import BudgetOverviewItem, BudgetOverviewState


HexRgbColorCode = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]


class CreateBudgetRequest(BaseModel):
    account_uuid: UUID
    category_uuid: UUID
    from_timestamp: int
    to_timestamp: int
    name: BudgetName
    description: BudgetDescription
    amount: BudgetAmount
    icon: Icon
    color_code: HexRgbColorCode

    @model_validator(mode="after")
    def validate_period(self) -> Self:
        if self.from_timestamp >= self.to_timestamp:
            raise ValueError("from_timestamp must be less than to_timestamp")
        return self


class UpdateBudgetRequest(BaseModel):
    category_uuid: UUID
    from_timestamp: int
    to_timestamp: int
    name: BudgetName
    description: BudgetDescription
    amount: BudgetAmount
    icon: Icon
    color_code: HexRgbColorCode

    @model_validator(mode="after")
    def validate_period(self) -> Self:
        if self.from_timestamp >= self.to_timestamp:
            raise ValueError("from_timestamp must be less than to_timestamp")
        return self


class BudgetResponse(BaseModel):
    uuid: UUID
    account_uuid: UUID
    category_uuid: UUID
    from_timestamp: int
    to_timestamp: int
    name: BudgetName
    description: BudgetDescription
    amount: BudgetAmount
    icon: Icon
    color_code: HexRgbColorCode

    @classmethod
    def from_budget(cls, budget: Budget) -> Self:
        return cls(
            uuid=budget.uuid,
            account_uuid=budget.account_uuid,
            category_uuid=budget.category_uuid,
            from_timestamp=budget.from_timestamp,
            to_timestamp=budget.to_timestamp,
            name=budget.name,
            description=budget.description,
            amount=budget.amount,
            icon=budget.icon,
            color_code=f"#{budget.color_code.hex().upper()}",
        )


class BudgetOverviewResponse(BudgetResponse):
    state: BudgetOverviewState
    spent_amount: int | None
    fulfilled: bool | None

    @classmethod
    def from_overview(cls, item: BudgetOverviewItem) -> Self:
        budget = item.budget
        return cls(
            **BudgetResponse.from_budget(budget).model_dump(),
            state=item.state,
            spent_amount=item.spent_amount,
            fulfilled=item.fulfilled,
        )


class BudgetOverviewPageResponse(BaseModel):
    items: list[BudgetOverviewResponse]
    next_cursor: str | None
