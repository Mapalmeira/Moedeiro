from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.ledger_grant import LedgerGrant, LedgerRole


class LedgerGrantRepository(ABC):
    @abstractmethod
    def create(self, user_uuid: UUID, ledger_uuid: UUID, role: LedgerRole, created_at: int) -> LedgerGrant:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> LedgerGrant | None:
        pass

    @abstractmethod
    def get_active(self, user_uuid: UUID, ledger_uuid: UUID) -> LedgerGrant | None:
        pass

    @abstractmethod
    def revoke(self, uuid: UUID, revoked_at: int) -> None:
        pass

    @abstractmethod
    def delete_inactive_before(self, timestamp: int) -> int:
        pass

    @abstractmethod
    def list_by_user(self, user_uuid: UUID) -> list[LedgerGrant]:
        pass

    @abstractmethod
    def list_by_ledger(self, ledger_uuid: UUID) -> list[LedgerGrant]:
        pass

    @abstractmethod
    def list_all(self) -> list[LedgerGrant]:
        pass
