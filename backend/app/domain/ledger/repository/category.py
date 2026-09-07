from abc import ABC, abstractmethod
from collections.abc import Collection
from uuid import UUID

from app.domain.appearance import Icon, RgbColorCode
from app.domain.ledger.model.category import Category, CategoryName
from app.domain.ledger.model.category_tree_node import CategoryTreeNode


class CategoryRepository(ABC):
    @abstractmethod
    def create(self, name: CategoryName, icon: Icon, color_code: RgbColorCode, parent_uuid: UUID | None) -> Category:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> Category | None:
        pass

    @abstractmethod
    def get_by_name(self, name: CategoryName) -> Category | None:
        pass

    @abstractmethod
    def get_many(self, uuids: Collection[UUID]) -> list[Category]:
        pass

    @abstractmethod
    def update_name(self, uuid: UUID, value: CategoryName) -> None:
        pass

    @abstractmethod
    def update_icon(self, uuid: UUID, value: Icon) -> None:
        pass

    @abstractmethod
    def update_color_code(self, uuid: UUID, value: RgbColorCode) -> None:
        pass

    @abstractmethod
    def update_parent(self, uuid: UUID, parent_uuid: UUID | None) -> None:
        pass

    @abstractmethod
    def count(self) -> int:
        pass

    @abstractmethod
    def get_tree(self, max_size: int) -> list[CategoryTreeNode]:
        pass

    @abstractmethod
    def is_in_use(self, uuid: UUID) -> bool:
        pass

    @abstractmethod
    def delete(self, uuid: UUID) -> None:
        pass
