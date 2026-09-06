from abc import ABC, abstractmethod
from collections.abc import Collection
from uuid import UUID

from app.domain.appearance import Icon, RgbColorCode
from app.domain.ledger.model.account import Account, AccountName, AccountNote


class AccountRepository(ABC):
    @abstractmethod
    def create(
        self,
        name: AccountName,
        note: AccountNote | None,
        currency_uuid: UUID,
        icon: Icon,
        color_code: RgbColorCode,
    ) -> Account:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> Account | None:
        pass

    @abstractmethod
    def get_many(self, uuids: Collection[UUID]) -> list[Account]:
        pass

    @abstractmethod
    def get_by_name(self, name: AccountName) -> Account | None:
        pass

    @abstractmethod
    def update_name(self, uuid: UUID, value: AccountName) -> None:
        pass

    @abstractmethod
    def update_note(self, uuid: UUID, value: AccountNote | None) -> None:
        pass

    @abstractmethod
    def update_icon(self, uuid: UUID, value: Icon) -> None:
        pass

    @abstractmethod
    def update_color_code(self, uuid: UUID, value: RgbColorCode) -> None:
        pass

    @abstractmethod
    def list_all(self) -> list[Account]:
        pass

    @abstractmethod
    def count(self) -> int:
        pass

    @abstractmethod
    def is_in_use(self, uuid: UUID) -> bool:
        pass

    @abstractmethod
    def delete(self, uuid: UUID) -> None:
        pass
