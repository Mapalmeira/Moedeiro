from pydantic import BaseModel

from app.domain.registry.model.user import Password, UserName


class LoginRequest(BaseModel):
    name: UserName
    password: Password
    remember: bool = False
