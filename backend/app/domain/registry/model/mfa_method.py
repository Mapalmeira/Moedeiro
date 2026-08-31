from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


MfaMethodType = Literal["TOTP"]


class MfaMethod(BaseModel):
    uuid: UUID
    user_uuid: UUID
    type: MfaMethodType
    secret_encrypted: bytes
    created_at: int = Field(ge=0)
