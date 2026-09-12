from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field
from typing_extensions import Self

from app.domain.appearance import Icon
from app.domain.ledger.model.account import Account, AccountName, AccountNote


HexRgbColorCode = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]


class CreateAccountRequest(BaseModel):
    name: AccountName
    note: AccountNote | None = None
    currency_uuid: UUID
    icon: Icon
    color_code: HexRgbColorCode


class UpdateAccountRequest(BaseModel):
    name: AccountName
    note: AccountNote | None = None
    icon: Icon
    color_code: HexRgbColorCode


class AccountResponse(BaseModel):
    uuid: UUID
    name: AccountName
    note: AccountNote | None
    currency_uuid: UUID
    icon: Icon
    color_code: HexRgbColorCode

    @classmethod
    def from_account(cls, account: Account) -> Self:
        return cls(
            uuid=account.uuid,
            name=account.name,
            note=account.note,
            currency_uuid=account.currency_uuid,
            icon=account.icon,
            color_code=f"#{account.color_code.hex().upper()}",
        )


class AccountBalanceResponse(BaseModel):
    account_uuid: UUID
    currency_uuid: UUID
    balance: int


class AccountBalanceListResponse(BaseModel):
    items: list[AccountBalanceResponse]
    total_balance: int | None
