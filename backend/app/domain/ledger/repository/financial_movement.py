from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.ledger.model.financial_movement import FinancialMovement, FinancialMovementItemName, FinancialMovementQuantity


class FinancialMovementRepository(ABC):
    @abstractmethod
    def create(
        self,
        financial_event_uuid: UUID,
        account_uuid: UUID,
        category_uuid: UUID,
        value: int,
        item_name: FinancialMovementItemName | None,
        quantity: FinancialMovementQuantity = 1,
    ) -> FinancialMovement:
        pass

    @abstractmethod
    def update(self, movement: FinancialMovement) -> None:
        pass

    @abstractmethod
    def delete(self, uuid: UUID) -> None:
        pass
