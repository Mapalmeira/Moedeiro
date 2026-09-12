from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self


TotpCode = Annotated[str, Field(min_length=6, max_length=6, pattern=r"^\d{6}$")]
TotpState = Literal["ENABLED", "DISABLED", "PENDING"]


class TotpStatus(BaseModel):
    state: TotpState
    provisioning_uri: str | None = None
    expires_at: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_pending_setup(self) -> Self:
        if self.state == "PENDING":
            if self.provisioning_uri is None or self.expires_at is None:
                raise ValueError("pending TOTP status requires provisioning_uri and expires_at")
        elif self.provisioning_uri is not None or self.expires_at is not None:
            raise ValueError("only pending TOTP status may include setup details")
        return self
