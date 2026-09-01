class FakePasswordHasher:
    def __init__(self):
        self.passwords: list[str] = []
        self.verifications: list[tuple[str, str]] = []

    def hash(self, password: str) -> str:
        self.passwords.append(password)
        return f"$argon2id$test${password}"

    def verify(self, password_hash: str, password: str) -> bool:
        self.verifications.append((password_hash, password))
        return password_hash == f"$argon2id$test${password}"


class FakeRateLimiter:
    def __init__(self):
        self.checks: list[tuple[str, str, str]] = []
        self.rejected_namespace: str | None = None

    def check(self, rate: str, namespace: str, key: str) -> None:
        from app.infrastructure.security.rate_limiter import RateLimitExceededError

        self.checks.append((rate, namespace, key))
        if namespace == self.rejected_namespace:
            raise RateLimitExceededError(17)


class FakeTotpAuthenticator:
    def __init__(self):
        self.secret = "FAKESECRET"
        self.valid_code = "123456"

    def create_secret(self) -> str:
        return self.secret

    def create_setup_token(self, user_uuid, secret: str, timestamp: int) -> str:
        return f"{user_uuid}:{secret}:{timestamp}"

    def get_setup_secret(self, setup_token: str, user_uuid, timestamp: int) -> str | None:
        expected_prefix = f"{user_uuid}:{self.secret}:"
        return self.secret if setup_token.startswith(expected_prefix) else None

    def provisioning_uri(self, secret: str, user_name: str) -> str:
        return f"otpauth://totp/Moedeiro:{user_name}?secret={secret}"

    def encrypt_secret(self, secret: str) -> bytes:
        return secret.encode("ascii")

    def decrypt_secret(self, encrypted_secret: bytes) -> str:
        return encrypted_secret.decode("ascii")

    def verify(self, secret: str, code: str, timestamp: int) -> bool:
        return secret == self.secret and code == self.valid_code
