from typing import Annotated, Self
from unicodedata import normalize
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


UserName = Annotated[str, Field(min_length=1, max_length=50)]
NormalizedUserName = Annotated[str, Field(min_length=1)]


def normalize_user_name(value: str) -> str:
    return normalize("NFKC", value.strip()).casefold()


class User(BaseModel):
    uuid: UUID
    name: UserName
    normalized_name: NormalizedUserName
    password_hash: str
    created_at: int = Field(ge=0)
    password_changed_at: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.normalized_name != normalize_user_name(self.name):
            raise ValueError("normalized_name must match name")
        if self.password_changed_at < self.created_at:
            raise ValueError("password_changed_at must not precede created_at")
        return self
