from app.domain.ledger.model.currency import Currency
from abc import ABC, abstractmethod
from uuid import UUID

class CurrencyRepository(ABC):
    @abstractmethod
    def create(
        self,
        name: str,
        prefix: str | None,
        suffix: str | None,
        decimal_places: int,
    ) -> None:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> Currency | None:
        pass

    @abstractmethod
    def update_name(self, uuid: UUID, value: str) -> None:
        pass

    @abstractmethod
    def update_prefix(self, uuid: UUID, value: str | None) -> None:
        pass

    @abstractmethod
    def update_suffix(self, uuid: UUID, value: str | None) -> None:
        pass

    @abstractmethod
    def list_all(self) -> list[Currency]:
        pass

    @abstractmethod
    def list_page(self, page_number: int, page_size: int, sort_key: str, ascending: bool) -> list[Currency]:
        pass
