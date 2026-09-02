from pydantic import BaseModel

from app.domain.registry.model.user import Password, UserName
from app.domain.registry.model.user_invitation import InvitationCode

class RegisterUserRequest(BaseModel):
    invitation_code: InvitationCode
    name: UserName
    password: Password
