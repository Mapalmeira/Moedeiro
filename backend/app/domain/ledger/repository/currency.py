from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.appearance import Icon, RgbColorCode
from app.domain.ledger.model.currency import Currency

class CurrencyRepository(ABC):
    @abstractmethod
    def create(
        self,
        name: str,
        prefix: str | None,
        suffix: str | None,
        decimal_places: int,
        icon: Icon,
        color_code: RgbColorCode,
    ) -> Currency:
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
    def update_icon(self, uuid: UUID, value: Icon) -> None:
        pass

    @abstractmethod
    def update_color_code(self, uuid: UUID, value: RgbColorCode) -> None:
        pass

    @abstractmethod
    def list_page(self, page_number: int, page_size: int, sort_key: str, ascending: bool) -> list[Currency]:
        pass

    @abstractmethod
    def is_in_use(self, uuid: UUID) -> bool:
        pass

    @abstractmethod
    def delete(self, uuid: UUID) -> None:
        pass
