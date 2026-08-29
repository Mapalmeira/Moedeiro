from typing import Self

from pydantic import BaseModel, Field

from app.domain.ledger.model.category import Category


class CategoryTreeNode(BaseModel):
    category: Category
    children: list[Self] = Field(default_factory=list)
