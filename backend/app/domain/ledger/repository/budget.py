from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.ledger.model.budget import Budget, BudgetAmount, BudgetDescription, BudgetName


class BudgetRepository(ABC):
    @abstractmethod
    def create(
        self,
        account_uuid: UUID,
        category_uuid: UUID,
        from_timestamp: int,
        to_timestamp: int,
        name: BudgetName,
        description: BudgetDescription | None,
        amount: BudgetAmount,
    ) -> Budget:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> Budget | None:
        pass

    @abstractmethod
    def get_by_name(self, name: BudgetName) -> Budget | None:
        pass

    @abstractmethod
    def update(self, budget: Budget) -> None:
        pass

    @abstractmethod
    def count(self) -> int:
        pass

    @abstractmethod
    def delete(self, uuid: UUID) -> None:
        pass
