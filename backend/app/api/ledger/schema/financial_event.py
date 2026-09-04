from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.domain.ledger.model.financial_event import FinancialEvent, FinancialEventDescription, FinancialEventType
from app.domain.ledger.model.financial_movement import FinancialMovement, FinancialMovementItemName, FinancialMovementQuantity


ExpenseValue = Annotated[int, Field(lt=0)]
IncomeValue = Annotated[int, Field(gt=0)]


class SimpleFinancialEventRequest(BaseModel):
    type: Literal["TRANSACTION"]
    occurred_at: int
    description: FinancialEventDescription
    account_uuid: UUID
    category_uuid: UUID
    value: int
    quantity: FinancialMovementQuantity = 1
    item_name: FinancialMovementItemName | None = None

    @field_validator("value")
    @classmethod
    def reject_zero_value(cls, value: int) -> int:
        if value == 0:
            raise ValueError("value must not be zero")
        return value


class ShoppingListMovementRequest(BaseModel):
    category_uuid: UUID
    value: ExpenseValue
    quantity: FinancialMovementQuantity = 1
    item_name: FinancialMovementItemName | None = None


class ShoppingListFinancialEventRequest(BaseModel):
    type: Literal["SHOPPING_LIST"]
    occurred_at: int
    description: FinancialEventDescription
    account_uuid: UUID
    movements: list[ShoppingListMovementRequest] = Field(min_length=1)


class AccountTransferFeeRequest(BaseModel):
    category_uuid: UUID
    value: ExpenseValue


class AccountTransferFinancialEventRequest(BaseModel):
    type: Literal["ACCOUNT_TRANSFER"]
    occurred_at: int
    description: FinancialEventDescription
    source_account_uuid: UUID
    source_category_uuid: UUID
    source_value: ExpenseValue
    destination_account_uuid: UUID
    destination_category_uuid: UUID
    destination_value: IncomeValue
    fee: AccountTransferFeeRequest | None = None


CreateFinancialEventRequest = Annotated[SimpleFinancialEventRequest | ShoppingListFinancialEventRequest | AccountTransferFinancialEventRequest, Field(discriminator="type")]


class UpdateSimpleFinancialEventRequest(BaseModel):
    type: Literal["TRANSACTION"]
    occurred_at: int
    description: FinancialEventDescription
    account_uuid: UUID
    category_uuid: UUID
    value: int
    quantity: FinancialMovementQuantity = 1
    item_name: FinancialMovementItemName | None = None

    @field_validator("value")
    @classmethod
    def reject_zero_value(cls, value: int) -> int:
        if value == 0:
            raise ValueError("value must not be zero")
        return value


class UpdateShoppingListMovementRequest(BaseModel):
    uuid: UUID | None = None
    category_uuid: UUID
    value: ExpenseValue
    quantity: FinancialMovementQuantity = 1
    item_name: FinancialMovementItemName | None = None


class UpdateShoppingListFinancialEventRequest(BaseModel):
    type: Literal["SHOPPING_LIST"]
    occurred_at: int
    description: FinancialEventDescription
    account_uuid: UUID
    movements: list[UpdateShoppingListMovementRequest] = Field(min_length=1)


class UpdateAccountTransferFinancialEventRequest(BaseModel):
    type: Literal["ACCOUNT_TRANSFER"]
    occurred_at: int
    description: FinancialEventDescription
    source_account_uuid: UUID
    source_category_uuid: UUID
    source_value: ExpenseValue
    destination_account_uuid: UUID
    destination_category_uuid: UUID
    destination_value: IncomeValue
    fee: AccountTransferFeeRequest | None = None


UpdateFinancialEventRequest = Annotated[UpdateSimpleFinancialEventRequest | UpdateShoppingListFinancialEventRequest | UpdateAccountTransferFinancialEventRequest, Field(discriminator="type")]


class FinancialMovementResponse(BaseModel):
    uuid: UUID
    account_uuid: UUID
    category_uuid: UUID
    value: int
    quantity: FinancialMovementQuantity
    item_name: FinancialMovementItemName | None

    @classmethod
    def from_movement(cls, movement: FinancialMovement) -> Self:
        return cls(uuid=movement.uuid, account_uuid=movement.account_uuid, category_uuid=movement.category_uuid, value=movement.value, quantity=movement.quantity, item_name=movement.item_name)


class FinancialEventResponse(BaseModel):
    uuid: UUID
    occurred_at: int
    description: FinancialEventDescription
    type: FinancialEventType
    movements: list[FinancialMovementResponse]

    @classmethod
    def from_event(cls, event: FinancialEvent) -> Self:
        return cls(
            uuid=event.uuid,
            occurred_at=event.occurred_at,
            description=event.description,
            type=event.type,
            movements=[FinancialMovementResponse.from_movement(movement) for movement in event.movements],
        )
