from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.ledger_grant import LedgerGrant, LedgerRole


class LedgerGrantRepository(ABC):
    @abstractmethod
    def create(self, grantee_uuid: UUID, ledger_uuid: UUID, role: LedgerRole, created_at: int) -> LedgerGrant:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> LedgerGrant | None:
        pass

    @abstractmethod
    def get_active_owner_by_ledger(self, ledger_uuid: UUID) -> LedgerGrant | None:
        pass

    @abstractmethod
    def revoke(self, uuid: UUID, revoked_at: int) -> None:
        pass

    @abstractmethod
    def delete_inactive_before(self, timestamp: int) -> int:
        pass

    @abstractmethod
    def list_by_grantee(self, grantee_uuid: UUID) -> list[LedgerGrant]:
        pass

    @abstractmethod
    def list_by_grantee_and_ledger(self, grantee_uuid: UUID, ledger_uuid: UUID) -> list[LedgerGrant]:
        pass

    @abstractmethod
    def list_by_ledger(self, ledger_uuid: UUID) -> list[LedgerGrant]:
        pass

    @abstractmethod
    def list_all(self) -> list[LedgerGrant]:
        pass
