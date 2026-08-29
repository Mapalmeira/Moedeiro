from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.access_invitation import AccessInvitation


class AccessInvitationRepository(ABC):
    @abstractmethod
    def create(self, ledger_uuid: UUID, secret_hash: bytes, created_at: int, expires_at: int) -> AccessInvitation:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> AccessInvitation | None:
        pass

    @abstractmethod
    def get_by_secret_hash(self, secret_hash: bytes) -> AccessInvitation | None:
        pass

    @abstractmethod
    def consume(self, uuid: UUID, consumed_at: int) -> bool:
        pass

    @abstractmethod
    def revoke(self, uuid: UUID, revoked_at: int) -> None:
        pass

    @abstractmethod
    def list_by_ledger(self, ledger_uuid: UUID) -> list[AccessInvitation]:
        pass
