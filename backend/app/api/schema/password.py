from pydantic import BaseModel

from app.domain.registry.model.crockford_code import CrockfordCode
from app.domain.registry.model.user import Password
from app.domain.registry.model.totp import TotpCode


class ChangePasswordRequest(BaseModel):
    current_password: Password
    new_password: Password
    totp_code: TotpCode | None = None


class ValidateRecoveryCodeRequest(BaseModel):
    recovery_code: CrockfordCode


class ResetPasswordRequest(BaseModel):
    recovery_code: CrockfordCode
    new_password: Password
