from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field
from typing_extensions import Self

from app.domain.ledger.model.cash_flow import CashFlow
from app.domain.ledger.model.cash_flow_sankey import CashFlowSankey, CashFlowSankeyLink, CashFlowSankeyNode, CashFlowSankeyNodeKind, CashFlowSankeySide


HexRgbColorCode = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]


class CashFlowResponse(BaseModel):
    currency_uuid: UUID
    income: int
    expense: int
    event_count: int
    income_movement_count: int
    expense_movement_count: int

    @classmethod
    def from_cash_flow(cls, cash_flow: CashFlow) -> Self:
        return cls.model_validate(cash_flow.model_dump())


class CashFlowSankeyNodeResponse(BaseModel):
    id: str
    kind: CashFlowSankeyNodeKind
    side: CashFlowSankeySide
    label: str
    color_code: HexRgbColorCode
    column: int
    order: int
    value: int
    category_uuid: UUID | None

    @classmethod
    def from_node(cls, node: CashFlowSankeyNode) -> Self:
        return cls(
            id=node.id,
            kind=node.kind,
            side=node.side,
            label=node.label,
            color_code=f"#{node.color_code.hex().upper()}",
            column=node.column,
            order=node.order,
            value=node.value,
            category_uuid=node.category_uuid,
        )


class CashFlowSankeyLinkResponse(BaseModel):
    source: str
    target: str
    value: int

    @classmethod
    def from_link(cls, link: CashFlowSankeyLink) -> Self:
        return cls.model_validate(link.model_dump())


class CashFlowSankeyResponse(BaseModel):
    account_uuid: UUID
    currency_uuid: UUID
    from_timestamp: int
    to_timestamp: int
    detail_level: int
    income: int
    expense: int
    nodes: list[CashFlowSankeyNodeResponse]
    links: list[CashFlowSankeyLinkResponse]

    @classmethod
    def from_sankey(cls, sankey: CashFlowSankey) -> Self:
        return cls(
            account_uuid=sankey.account_uuid,
            currency_uuid=sankey.currency_uuid,
            from_timestamp=sankey.from_timestamp,
            to_timestamp=sankey.to_timestamp,
            detail_level=sankey.detail_level,
            income=sankey.income,
            expense=sankey.expense,
            nodes=[CashFlowSankeyNodeResponse.from_node(node) for node in sankey.nodes],
            links=[CashFlowSankeyLinkResponse.from_link(link) for link in sankey.links],
        )
