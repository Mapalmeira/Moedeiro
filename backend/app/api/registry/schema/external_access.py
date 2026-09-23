from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.registry.model.totp import TotpCode
from app.domain.registry.model.user import Password


class ExternalAccessCredentialRequest(BaseModel):
    current_password: Password
    totp_code: TotpCode | None = None


class CreateExternalAccessRequest(ExternalAccessCredentialRequest):
    name: str = Field(min_length=1, max_length=50)


RevokeExternalAccessRequest = ExternalAccessCredentialRequest


class ExternalAccessGrantResponse(BaseModel):
    grant_uuid: UUID
    external_access_uuid: UUID
    name: str
    created_at: int


class CreatedExternalAccessGrantResponse(ExternalAccessGrantResponse):
    token: str = Field(
        description=(
            "Bearer token for this external access and its ledger. It is returned only once, when the access is created, "
            "and must be sent only over HTTPS."
        )
    )
