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
