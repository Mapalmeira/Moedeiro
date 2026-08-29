from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.ledger.model.tag import Tag
from app.domain.ledger.model.financial_event import FinancialEvent, FinancialEventType
from app.domain.ledger.model.financial_event_filter import FinancialEventFilter


class FinancialEventRepository(ABC):
    @abstractmethod
    def create(
        self,
        occurred_at: int,
        description: str,
        type: FinancialEventType,
    ) -> FinancialEvent:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> FinancialEvent | None:
        pass

    @abstractmethod
    def update_occurred_at(self, uuid: UUID, value: int) -> None:
        pass

    @abstractmethod
    def update_description(self, uuid: UUID, value: str) -> None:
        pass

    @abstractmethod
    def add_tag(self, financial_event_uuid: UUID, tag_uuid: UUID) -> None:
        pass

    @abstractmethod
    def remove_tag(self, financial_event_uuid: UUID, tag_uuid: UUID) -> None:
        pass

    @abstractmethod
    def list_tags(self, financial_event_uuid: UUID) -> list[Tag]:
        pass

    @abstractmethod
    def list_all(self) -> list[FinancialEvent]:
        pass

    @abstractmethod
    def list_filtered(self, filters: FinancialEventFilter) -> list[FinancialEvent]:
        pass

    @abstractmethod
    def list_page(
        self,
        page_number: int,
        page_size: int,
        ascending: bool,
        filters: FinancialEventFilter,
    ) -> list[FinancialEvent]:
        pass
