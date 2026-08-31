from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.user_invitation import DEFAULT_EXPIRATION_TIMEOUT_SECONDS, UserInvitation


class UserInvitationRepository(ABC):
    @abstractmethod
    def create(self, secret_hash: bytes, created_at: int, expiration_timeout_seconds: int = DEFAULT_EXPIRATION_TIMEOUT_SECONDS) -> UserInvitation:
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
    def revoke(self, uuid: UUID, revoked_at: int) -> None:
        pass

    @abstractmethod
    def list_all(self) -> list[UserInvitation]:
        pass
