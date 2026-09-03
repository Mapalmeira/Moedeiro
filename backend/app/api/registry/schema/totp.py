from pydantic import BaseModel

from app.domain.registry.model.totp import TotpCode
from app.domain.registry.model.user import Password


class StartTotpSetupRequest(BaseModel):
    current_password: Password


class StartTotpSetupResponse(BaseModel):
    provisioning_uri: str


class ConfirmTotpRequest(BaseModel):
    code: TotpCode


class DisableTotpRequest(BaseModel):
    current_password: Password
    code: TotpCode
