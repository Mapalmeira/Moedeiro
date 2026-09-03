from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.appearance import Icon, RgbColorCode
from app.domain.registry.model.ledger import Ledger, LedgerName


class LedgerRepository(ABC):
    @abstractmethod
    def create(self, uuid: UUID, name: LedgerName, path: str, icon: Icon, color_code: RgbColorCode) -> Ledger:
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
    def update_name(self, uuid: UUID, value: LedgerName) -> None:
        pass

    @abstractmethod
    def update_icon(self, uuid: UUID, value: Icon) -> None:
        pass

    @abstractmethod
    def update_color_code(self, uuid: UUID, value: RgbColorCode) -> None:
        pass

    @abstractmethod
    def delete(self, uuid: UUID) -> None:
        pass

    @abstractmethod
    def list_all(self) -> list[Ledger]:
        pass

    @abstractmethod
    def list_owned_by_user(self, user_uuid: UUID) -> list[Ledger]:
        pass
