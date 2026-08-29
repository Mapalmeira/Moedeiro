from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.ledger.model.financial_movement import FinancialMovement


class FinancialMovementRepository(ABC):
    @abstractmethod
    def create(
        self,
        financial_event_uuid: UUID,
        account_uuid: UUID,
        category_uuid: UUID,
        value: int,
        item_name: str | None,
    ) -> FinancialMovement:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> FinancialMovement | None:
        pass

    @abstractmethod
    def update_value(self, uuid: UUID, value: int) -> None:
        pass

    @abstractmethod
    def update_item_name(self, uuid: UUID, value: str | None) -> None:
        pass

    @abstractmethod
    def update_category(self, uuid: UUID, category_uuid: UUID) -> None:
        pass

    @abstractmethod
    def list_by_financial_event(
        self,
        financial_event_uuid: UUID,
    ) -> list[FinancialMovement]:
        pass

    @abstractmethod
    def list_all(self) -> list[FinancialMovement]:
        pass

    @abstractmethod
    def list_page(
        self,
        page_number: int,
        page_size: int,
        sort_key: str,
        ascending: bool,
    ) -> list[FinancialMovement]:
        pass
