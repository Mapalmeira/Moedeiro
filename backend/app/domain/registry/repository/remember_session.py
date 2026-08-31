from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.remember_session import RememberSession


class RememberSessionRepository(ABC):
    @abstractmethod
    def create(self, user_uuid: UUID, token_hash: bytes, created_at: int, expires_at: int) -> RememberSession:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> RememberSession | None:
        pass

    @abstractmethod
    def get_by_token_hash(self, token_hash: bytes) -> RememberSession | None:
        pass

    @abstractmethod
    def rotate(self, uuid: UUID, expected_token_hash: bytes, new_token_hash: bytes, last_used_at: int) -> bool:
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
