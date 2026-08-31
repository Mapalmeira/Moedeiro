from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.ledger import Ledger


class LedgerRepository(ABC):
    @abstractmethod
    def create(self, name: str, path: str, icon: str, color_code: bytes) -> Ledger:
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
    def update_name(self, uuid: UUID, value: str) -> None:
        pass

    @abstractmethod
    def update_icon(self, uuid: UUID, value: str) -> None:
        pass

    @abstractmethod
    def update_color_code(self, uuid: UUID, value: bytes) -> None:
        pass

    @abstractmethod
    def delete(self, uuid: UUID) -> None:
        pass

    @abstractmethod
    def list_all(self) -> list[Ledger]:
        pass
