from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.ledger_grant import LedgerGrant
from app.domain.registry.model.ledger_token_grant import LedgerTokenGrant


class LedgerTokenGrantRepository(ABC):
    @abstractmethod
    def create(self, grant: LedgerGrant, name: str, token_hash: bytes) -> LedgerTokenGrant:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> LedgerTokenGrant | None:
        pass

    @abstractmethod
    def get_by_token_hash(self, token_hash: bytes) -> LedgerTokenGrant | None:
        pass
