from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.appearance import Icon, RgbColorCode
from app.domain.ledger.model.budget import Budget, BudgetAmount, BudgetDescription, BudgetName


class BudgetRepository(ABC):
    @abstractmethod
    def create(
        self,
        category_uuid: UUID,
        currency_uuid: UUID,
        from_timestamp: int,
        to_timestamp: int,
        name: BudgetName,
        description: BudgetDescription,
        amount: BudgetAmount,
        icon: Icon,
        color_code: RgbColorCode,
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
    def add_account(self, budget_uuid: UUID, account_uuid: UUID) -> None:
        pass

    @abstractmethod
    def remove_account(self, budget_uuid: UUID, account_uuid: UUID) -> None:
        pass

    @abstractmethod
    def list_page(
        self,
        page_number: int,
        page_size: int,
        sort_key: str,
        ascending: bool,
    ) -> list[Budget]:
        pass

    @abstractmethod
    def count(self) -> int:
        pass

    @abstractmethod
    def delete(self, uuid: UUID) -> None:
        pass
