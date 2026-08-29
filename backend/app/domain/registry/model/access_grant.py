from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


AuthenticationMethod = Literal["WEBCRYPTO", "WEBAUTHN"]
GrantAlgorithm = Literal["ES256"]


class AccessGrant(BaseModel):
    uuid: UUID
    ledger_uuid: UUID
    authentication_method: AuthenticationMethod
    label: str | None = Field(default=None, max_length=30)
    public_key: bytes = Field(min_length=1, max_length=4096)
    algorithm: GrantAlgorithm
    credential_id: bytes | None = Field(default=None, min_length=1, max_length=1023)
    signature_counter: int | None = Field(default=None, ge=0)
    created_at: int = Field(ge=0)
    revoked_at: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_state(self) -> "AccessGrant":
        webauthn_values = (self.credential_id, self.signature_counter)
        if self.authentication_method == "WEBCRYPTO" and any(value is not None for value in webauthn_values):
            raise ValueError("WebCrypto grants cannot contain WebAuthn state")
        if self.authentication_method == "WEBAUTHN" and any(value is None for value in webauthn_values):
            raise ValueError("WebAuthn grants require credential and authenticator state")
        if self.revoked_at is not None and self.revoked_at < self.created_at:
            raise ValueError("revoked_at must not precede created_at")
        return self
