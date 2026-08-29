from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.ledger.model.tag import Tag
from app.domain.ledger.model.transaction_event import TransactionEvent, TransactionEventType
from app.domain.ledger.model.transaction_event_filter import TransactionEventFilter


class TransactionEventRepository(ABC):
    @abstractmethod
    def create(
        self,
        occurred_at: int,
        description: str,
        type: TransactionEventType,
    ) -> TransactionEvent:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> TransactionEvent | None:
        pass

    @abstractmethod
    def update_occurred_at(self, uuid: UUID, value: int) -> None:
        pass

    @abstractmethod
    def update_description(self, uuid: UUID, value: str) -> None:
        pass

    @abstractmethod
    def add_tag(self, transaction_event_uuid: UUID, tag_uuid: UUID) -> None:
        pass

    @abstractmethod
    def remove_tag(self, transaction_event_uuid: UUID, tag_uuid: UUID) -> None:
        pass

    @abstractmethod
    def list_tags(self, transaction_event_uuid: UUID) -> list[Tag]:
        pass

    @abstractmethod
    def list_all(self) -> list[TransactionEvent]:
        pass

    @abstractmethod
    def list_filtered(self, filters: TransactionEventFilter) -> list[TransactionEvent]:
        pass

    @abstractmethod
    def list_page(
        self,
        page_number: int,
        page_size: int,
        ascending: bool,
        filters: TransactionEventFilter,
    ) -> list[TransactionEvent]:
        pass
