from typing import Protocol


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str:
        pass
