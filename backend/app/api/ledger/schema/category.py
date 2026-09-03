from __future__ import annotations

from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.appearance import Icon
from app.domain.ledger.model.category import Category, CategoryName
from app.domain.ledger.model.category_tree_node import CategoryTreeNode


HexRgbColorCode = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]


class CreateCategoryRequest(BaseModel):
    name: CategoryName
    icon: Icon
    color_code: HexRgbColorCode
    parent_uuid: UUID | None = None


class UpdateCategoryRequest(BaseModel):
    name: CategoryName
    icon: Icon
    color_code: HexRgbColorCode
    parent_uuid: UUID | None = None


class CategoryResponse(BaseModel):
    uuid: UUID
    name: CategoryName
    icon: Icon
    color_code: HexRgbColorCode
    parent_uuid: UUID | None

    @classmethod
    def from_category(cls, category: Category) -> Self:
        return cls(
            uuid=category.uuid,
            name=category.name,
            icon=category.icon,
            color_code=f"#{category.color_code.hex().upper()}",
            parent_uuid=category.parent_uuid,
        )


class CategoryTreeNodeResponse(BaseModel):
    category: CategoryResponse
    children: list[CategoryTreeNodeResponse]

    @classmethod
    def from_node(cls, node: CategoryTreeNode) -> Self:
        return cls(category=CategoryResponse.from_category(node.category), children=[cls.from_node(child) for child in node.children])
