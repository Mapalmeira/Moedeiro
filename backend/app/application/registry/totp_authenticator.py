from typing import Protocol
from uuid import UUID

from app.domain.registry.model.totp import TotpCode, TotpSetupToken


class TotpAuthenticator(Protocol):
    def create_secret(self) -> str:
        pass

    def create_setup_token(self, user_uuid: UUID, secret: str, timestamp: int) -> TotpSetupToken:
        pass

    def get_setup_secret(self, setup_token: TotpSetupToken, user_uuid: UUID, timestamp: int) -> str | None:
        pass

    def provisioning_uri(self, secret: str, user_name: str) -> str:
        pass

    def encrypt_secret(self, secret: str) -> bytes:
        pass

    def decrypt_secret(self, encrypted_secret: bytes) -> str:
        pass

    def verify(self, secret: str, code: TotpCode, timestamp: int) -> bool:
        pass
