from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.ledger import Ledger

class LedgerRepository(ABC):
    @abstractmethod
    def create(self, path: str) -> None:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> Ledger | None:
        pass

    @abstractmethod
    def get_by_path(self, path: str) -> Ledger | None:
        pass

    @abstractmethod
    def update_path(self, uuid: UUID, value: str) -> None:
        pass

    @abstractmethod
    def list_all(self) -> list[Ledger]:
        pass

    @abstractmethod
    def list_page(
        self,
        page_number: int,
        page_size: int,
        sort_key: str,
        ascending: bool,
    ) -> list[Ledger]:
        pass
