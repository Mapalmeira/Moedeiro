from argon2 import PasswordHasher as PasswordHasherImplementation
from argon2.exceptions import VerificationError

from app.application.registry.password_hasher import PasswordHasher
from app.domain.registry.model.user import Password


class Argon2PasswordHasher(PasswordHasher):
    def __init__(self):
        self._implementation = PasswordHasherImplementation(time_cost=2, memory_cost=19456, parallelism=1, hash_len=32, salt_len=16)

    def hash(self, password: Password) -> str:
        return self._implementation.hash(password)

    def verify(self, password_hash: str, password: Password) -> bool:
        try:
            return self._implementation.verify(password_hash, password)
        except VerificationError:
            return False
