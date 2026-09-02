class FakeCredentialOperationExecutor:
    def __init__(self):
        self.reject = False

    async def run(self, operation):
        if self.reject:
            from app.infrastructure.credential_operation_executor import CredentialOperationCapacityExceededError

            raise CredentialOperationCapacityExceededError
        return operation()

    def shutdown(self) -> None:
        pass


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
        self._counter = 0
        self.fixed_counter: int | None = None

    def create_secret(self) -> str:
        return self.secret

    def provisioning_uri(self, secret: str, user_name: str) -> str:
        return f"otpauth://totp/Moedeiro:{user_name}?secret={secret}"

    def encrypt_secret(self, secret: str) -> bytes:
        return secret.encode("ascii")

    def decrypt_secret(self, encrypted_secret: bytes) -> str:
        return encrypted_secret.decode("ascii")

    def verify(self, secret: str, code: str, timestamp: int) -> int | None:
        if secret != self.secret or code != self.valid_code:
            return None
        if self.fixed_counter is not None:
            return self.fixed_counter
        self._counter += 1
        return self._counter
