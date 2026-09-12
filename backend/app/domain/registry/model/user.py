import re
from typing import Annotated
from unicodedata import normalize
from uuid import UUID

from pydantic import AfterValidator, BaseModel, Field, model_validator
from typing_extensions import Self


def normalize_user_name(value: str) -> str:
    return normalize("NFKC", value.strip()).casefold()


def validate_user_name(value: str) -> str:
    if not normalize_user_name(value):
        raise ValueError("name must contain a non-whitespace character")
    if re.fullmatch(r"[A-Za-z0-9._~-]+", value) is None:
        raise ValueError("name must contain only URI-safe ASCII characters")
    return value


UserName = Annotated[str, Field(min_length=1, max_length=50), AfterValidator(validate_user_name)]
NormalizedUserName = Annotated[str, Field(min_length=1)]
Password = Annotated[str, Field(min_length=8, max_length=128)]


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
