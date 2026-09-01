from pydantic import BaseModel

from app.domain.registry.model.user import Password, UserName
from app.domain.registry.model.totp import TotpCode


class LoginRequest(BaseModel):
    name: UserName
    password: Password
    totp_code: TotpCode | None = None
    remember: bool = False
