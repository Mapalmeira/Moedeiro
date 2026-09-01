import base64
import hashlib
import hmac
import secrets
import struct

from cryptography.fernet import Fernet

from app.application.registry.totp_authenticator import TotpAuthenticator
from app.domain.registry.model.totp import TotpCode


class FernetTotpAuthenticator(TotpAuthenticator):
    _ISSUER = "Moedeiro"
    def __init__(self, encryption_key: str):
        self._fernet = Fernet(encryption_key.encode("ascii"))

    def create_secret(self) -> str:
        return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")

    def provisioning_uri(self, secret: str, user_name: str) -> str:
        label = f"{self._ISSUER}:{user_name}"
        return f"otpauth://totp/{label}?secret={secret}&issuer={self._ISSUER}&algorithm=SHA1&digits=6&period=30"

    def encrypt_secret(self, secret: str) -> bytes:
        return self._fernet.encrypt(secret.encode("ascii"))

    def decrypt_secret(self, encrypted_secret: bytes) -> str:
        return self._fernet.decrypt(encrypted_secret).decode("ascii")

    def verify(self, secret: str, code: TotpCode, timestamp: int) -> bool:
        for counter in range((timestamp // 30) - 1, (timestamp // 30) + 2):
            if counter >= 0 and hmac.compare_digest(self._code(secret, counter), code):
                return True
        return False

    @staticmethod
    def _code(secret: str, counter: int) -> str:
        key = base64.b32decode(secret + "=" * (-len(secret) % 8))
        digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
        return f"{value % 1_000_000:06d}"
