from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.user_invitation import UserInvitation


class UserInvitationRepository(ABC):
    @abstractmethod
    def create(self, secret_hash: bytes, created_at: int, expires_at: int) -> UserInvitation:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> UserInvitation | None:
        pass

    @abstractmethod
    def get_by_secret_hash(self, secret_hash: bytes) -> UserInvitation | None:
        pass

    @abstractmethod
    def consume(self, uuid: UUID, consumed_at: int) -> bool:
        pass

    @abstractmethod
    def delete(self, uuid: UUID) -> bool:
        pass

    @abstractmethod
    def delete_inactive_before(self, timestamp: int) -> int:
        pass

    @abstractmethod
    def list_all(self) -> list[UserInvitation]:
        pass
