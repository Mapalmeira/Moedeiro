from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.domain.appearance import RgbColorCode


CashFlowSankeySide = Literal["income", "account", "expense"]
CashFlowSankeyNodeKind = Literal["account", "category"]


class CashFlowCategoryTotal(BaseModel):
    category_uuid: UUID
    income: int
    expense: int


class CashFlowSankeyNode(BaseModel):
    id: str
    kind: CashFlowSankeyNodeKind
    side: CashFlowSankeySide
    label: str
    color_code: RgbColorCode
    column: int
    order: int
    value: int
    category_uuid: UUID | None = None


class CashFlowSankeyLink(BaseModel):
    source: str
    target: str
    value: int


class CashFlowSankey(BaseModel):
    account_uuid: UUID
    currency_uuid: UUID
    from_timestamp: int
    to_timestamp: int
    detail_level: int
    income: int
    expense: int
    nodes: list[CashFlowSankeyNode]
    links: list[CashFlowSankeyLink]
