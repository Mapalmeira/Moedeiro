from typing import Protocol

from app.domain.registry.model.user import Password


class PasswordHasher(Protocol):
    def hash(self, password: Password) -> str:
        pass

    def verify(self, password_hash: str, password: Password) -> bool:
        pass
