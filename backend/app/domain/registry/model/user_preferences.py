from typing import Literal
from uuid import UUID

from pydantic import BaseModel


Theme = Literal["LIGHT", "DARK"]
Language = Literal["pt-BR", "en"]


class UserPreferences(BaseModel):
    user_uuid: UUID
    language: Language
    theme: Theme
