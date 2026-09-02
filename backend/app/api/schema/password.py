from pydantic import BaseModel

from app.domain.registry.model.recovery_code import RecoveryCodeValue
from app.domain.registry.model.totp import TotpCode
from app.domain.registry.model.user import Password, UserName


class ChangePasswordRequest(BaseModel):
    current_password: Password
    new_password: Password
    totp_code: TotpCode | None = None


class ResetPasswordRequest(BaseModel):
    name: UserName
    recovery_code: RecoveryCodeValue
    new_password: Password
    totp_code: TotpCode | None = None
