from typing import Protocol
from app.domain.registry.model.totp import TotpCode


class TotpAuthenticator(Protocol):
    def create_secret(self) -> str:
        pass

    def provisioning_uri(self, secret: str, user_name: str) -> str:
        pass

    def encrypt_secret(self, secret: str) -> bytes:
        pass

    def decrypt_secret(self, encrypted_secret: bytes) -> str:
        pass

    def verify(self, secret: str, code: TotpCode, timestamp: int) -> bool:
        pass
