from threading import BoundedSemaphore

from app.application.registry.password_hasher import PasswordHasher
from app.domain.registry.model.user import Password


class PasswordHashCapacityExceededError(Exception):
    pass


class ConcurrentPasswordHasher(PasswordHasher):
    def __init__(self, password_hasher: PasswordHasher, semaphore: BoundedSemaphore):
        self._password_hasher = password_hasher
        self._semaphore = semaphore

    def hash(self, password: Password) -> str:
        return self._run(self._password_hasher.hash, password)

    def verify(self, password_hash: str, password: Password) -> bool:
        return self._run(self._password_hasher.verify, password_hash, password)

    def _run(self, operation, *arguments):
        if not self._semaphore.acquire(blocking=False):
            raise PasswordHashCapacityExceededError
        try:
            return operation(*arguments)
        finally:
            self._semaphore.release()
