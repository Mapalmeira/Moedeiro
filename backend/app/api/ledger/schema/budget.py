from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.domain.appearance import Icon
from app.domain.ledger.model.budget import Budget, BudgetAmount, BudgetDescription, BudgetName
from app.domain.ledger.model.budget_status import BudgetStatus


BudgetSortKey = Literal["from_timestamp", "to_timestamp", "name", "description", "amount"]
HexRgbColorCode = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]


class CreateBudgetRequest(BaseModel):
    category_uuid: UUID
    currency_uuid: UUID
    from_timestamp: int
    to_timestamp: int
    name: BudgetName
    description: BudgetDescription
    amount: BudgetAmount
    icon: Icon
    color_code: HexRgbColorCode
    account_uuids: set[UUID] = Field(default_factory=set)

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
    account_uuids: set[UUID] = Field(default_factory=set)

    @model_validator(mode="after")
    def validate_period(self) -> Self:
        if self.from_timestamp >= self.to_timestamp:
            raise ValueError("from_timestamp must be less than to_timestamp")
        return self


class BudgetResponse(BaseModel):
    uuid: UUID
    category_uuid: UUID
    currency_uuid: UUID
    from_timestamp: int
    to_timestamp: int
    name: BudgetName
    description: BudgetDescription
    amount: BudgetAmount
    icon: Icon
    color_code: HexRgbColorCode
    account_uuids: list[UUID]

    @classmethod
    def from_budget(cls, budget: Budget) -> Self:
        return cls(
            uuid=budget.uuid,
            category_uuid=budget.category_uuid,
            currency_uuid=budget.currency_uuid,
            from_timestamp=budget.from_timestamp,
            to_timestamp=budget.to_timestamp,
            name=budget.name,
            description=budget.description,
            amount=budget.amount,
            icon=budget.icon,
            color_code=f"#{budget.color_code.hex().upper()}",
            account_uuids=budget.account_uuids,
        )


class BudgetStatusResponse(BaseModel):
    budget_uuid: UUID
    budgeted_amount: BudgetAmount
    spent_amount: BudgetAmount
    over_budget: bool

    @classmethod
    def from_status(cls, budget_status: BudgetStatus) -> Self:
        return cls(
            budget_uuid=budget_status.budget_uuid,
            budgeted_amount=budget_status.budgeted_amount,
            spent_amount=budget_status.spent_amount,
            over_budget=budget_status.over_budget,
        )
