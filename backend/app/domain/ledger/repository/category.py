from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.ledger.model.category import Category


class CategoryRepository(ABC):
    @abstractmethod
    def create(self, name: str, parent_uuid: UUID | None) -> None:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> Category | None:
        pass

    @abstractmethod
    def update_name(self, uuid: UUID, value: str) -> None:
        pass

    @abstractmethod
    def update_parent(self, uuid: UUID, parent_uuid: UUID | None) -> None:
        pass

    @abstractmethod
    def list_all(self) -> list[Category]:
        pass

    @abstractmethod
    def list_page(
        self,
        page_number: int,
        page_size: int,
        sort_key: str,
        ascending: bool,
    ) -> list[Category]:
        pass
