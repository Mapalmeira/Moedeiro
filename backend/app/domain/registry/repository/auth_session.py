from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.auth_session import AuthSession


class AuthSessionRepository(ABC):
    @abstractmethod
    def create(self, user_uuid: UUID, token_hash: bytes, created_at: int) -> AuthSession:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> AuthSession | None:
        pass

    @abstractmethod
    def get_by_token_hash(self, token_hash: bytes) -> AuthSession | None:
        pass

    @abstractmethod
    def update_last_activity(self, uuid: UUID, last_activity_at: int) -> None:
        pass

    @abstractmethod
    def revoke(self, uuid: UUID, revoked_at: int) -> None:
        pass

    @abstractmethod
    def revoke_by_user(self, user_uuid: UUID, revoked_at: int) -> None:
        pass

    @abstractmethod
    def list_by_user(self, user_uuid: UUID) -> list[AuthSession]:
        pass
