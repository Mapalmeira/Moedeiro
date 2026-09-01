from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.appearance import Icon, RgbColorCode

CategoryName = Annotated[str, Field(min_length=1, max_length=30)]
MAX_CATEGORY_DEPTH = 5


class Category(BaseModel):
    uuid: UUID
    name: CategoryName
    icon: Icon
    color_code: RgbColorCode
    parent_uuid: UUID | None = None
