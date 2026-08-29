from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.ledger.model.account import Account


class AccountRepository(ABC):
    @abstractmethod
    def create(
        self,
        name: str,
        note: str | None,
        currency_uuid: UUID,
    ) -> Account:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> Account | None:
        pass

    @abstractmethod
    def update_name(self, uuid: UUID, value: str) -> None:
        pass

    @abstractmethod
    def update_note(self, uuid: UUID, value: str | None) -> None:
        pass

    @abstractmethod
    def list_all(self) -> list[Account]:
        pass

    @abstractmethod
    def list_page(
        self,
        page_number: int,
        page_size: int,
        sort_key: str,
        ascending: bool,
    ) -> list[Account]:
        pass
