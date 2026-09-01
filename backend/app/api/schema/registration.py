from typing import Annotated
from pydantic import BaseModel, Field, field_validator
from app.domain.registry.model.user import normalize_user_name

InvitationCode = Annotated[str, Field(min_length=16, max_length=16, pattern=r"^[0-9ABCDEFGHJKMNPQRSTVWXYZ]{16}$")]
UserName = Annotated[str, Field(min_length=1, max_length=50)]
Password = Annotated[str, Field(min_length=12, max_length=128)]

class ValidateInvitationRequest(BaseModel):
    invitation_code: InvitationCode

class RegisterUserRequest(BaseModel):
    invitation_code: InvitationCode
    name: UserName
    password: Password

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not normalize_user_name(value):
            raise ValueError("name must contain a non-whitespace character")
        return value
