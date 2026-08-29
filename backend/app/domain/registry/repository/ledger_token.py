from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.ledger_token import LedgerToken

class LedgerTokenRepository(ABC):
    @abstractmethod
    def create(
        self,
        ledger_uuid: UUID,
        token_hash: str,
        label: str | None,
        created_at: int,
    ) -> LedgerToken:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> LedgerToken | None:
        pass

    @abstractmethod
    def get_by_token_hash(self, token_hash: str) -> LedgerToken | None:
        pass

    @abstractmethod
    def update_label(self, uuid: UUID, value: str | None) -> None:
        pass

    @abstractmethod
    def revoke(self, uuid: UUID, revoked_at: int) -> None:
        pass

    @abstractmethod
    def list_by_ledger(self, ledger_uuid: UUID) -> list[LedgerToken]:
        pass

    @abstractmethod
    def list_all(self) -> list[LedgerToken]:
        pass

    @abstractmethod
    def list_page(
        self,
        page_number: int,
        page_size: int,
        sort_key: str,
        ascending: bool,
    ) -> list[LedgerToken]:
        pass
