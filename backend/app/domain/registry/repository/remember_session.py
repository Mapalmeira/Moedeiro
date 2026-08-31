from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.remember_session import DEFAULT_EXPIRATION_TIMEOUT_SECONDS, RememberSession


class RememberSessionRepository(ABC):
    @abstractmethod
    def create(self, user_uuid: UUID, token_hash: bytes, created_at: int, expiration_timeout_seconds: int = DEFAULT_EXPIRATION_TIMEOUT_SECONDS) -> RememberSession:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> RememberSession | None:
        pass

    @abstractmethod
    def get_by_token_hash(self, token_hash: bytes) -> RememberSession | None:
        pass

    @abstractmethod
    def rotate(self, uuid: UUID, token_hash: bytes, last_used_at: int) -> bool:
        pass

    @abstractmethod
    def revoke(self, uuid: UUID, revoked_at: int) -> None:
        pass

    @abstractmethod
    def revoke_by_user(self, user_uuid: UUID, revoked_at: int) -> None:
        pass

    @abstractmethod
    def list_by_user(self, user_uuid: UUID) -> list[RememberSession]:
        pass
