from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.ledger.model.account import Account
from app.domain.ledger.model.budget import Budget


class BudgetRepository(ABC):
    @abstractmethod
    def create(
        self,
        category_uuid: UUID,
        currency_uuid: UUID,
        from_timestamp: int,
        to_timestamp: int,
        name: str,
        description: str,
        amount: int,
    ) -> None:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> Budget | None:
        pass

    @abstractmethod
    def update_period(
        self,
        uuid: UUID,
        from_timestamp: int,
        to_timestamp: int,
    ) -> None:
        pass

    @abstractmethod
    def update_name(self, uuid: UUID, value: str) -> None:
        pass

    @abstractmethod
    def update_description(self, uuid: UUID, value: str) -> None:
        pass

    @abstractmethod
    def update_amount(self, uuid: UUID, value: int) -> None:
        pass

    @abstractmethod
    def update_category(self, uuid: UUID, category_uuid: UUID) -> None:
        pass

    @abstractmethod
    def add_account(self, budget_uuid: UUID, account_uuid: UUID) -> None:
        pass

    @abstractmethod
    def remove_account(self, budget_uuid: UUID, account_uuid: UUID) -> None:
        pass

    @abstractmethod
    def list_accounts(self, budget_uuid: UUID) -> list[Account]:
        pass

    @abstractmethod
    def list_all(self) -> list[Budget]:
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
