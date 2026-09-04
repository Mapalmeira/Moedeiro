from abc import ABC, abstractmethod
from uuid import UUID

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
    def list_after(
        self,
        page_size: int,
        ascending: bool,
        filters: FinancialEventFilter,
        occurred_at: int | None,
        uuid: UUID | None,
    ) -> list[FinancialEvent]:
        pass

    @abstractmethod
    def delete(self, uuid: UUID) -> None:
        pass
