from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.ledger.model.tag import Tag


class TagRepository(ABC):
    @abstractmethod
    def create(self, name: str) -> Tag:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> Tag | None:
        pass

    @abstractmethod
    def update_name(self, uuid: UUID, value: str) -> None:
        pass

    @abstractmethod
    def list_all(self) -> list[Tag]:
        pass

    @abstractmethod
    def list_page(
        self,
        page_number: int,
        page_size: int,
        sort_key: str,
        ascending: bool,
    ) -> list[Tag]:
        pass
