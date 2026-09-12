from pydantic import BaseModel, Field
from typing_extensions import Self

from app.domain.ledger.model.category import Category


class CategoryTreeNode(BaseModel):
    category: Category
    children: list[Self] = Field(default_factory=list)
