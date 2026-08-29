from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.ledger.model.category import Category
from app.domain.ledger.model.category_tree_node import CategoryTreeNode


class CategoryRepository(ABC):
    @abstractmethod
    def create(self, name: str, icon: str, color_code: bytes, parent_uuid: UUID | None) -> Category:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> Category | None:
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
    def update_parent(self, uuid: UUID, parent_uuid: UUID | None) -> None:
        pass

    @abstractmethod
    def list_all(self) -> list[Category]:
        pass

    @abstractmethod
    def get_tree(self) -> list[CategoryTreeNode]:
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
