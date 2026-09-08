from abc import ABC, abstractmethod
from collections.abc import Collection
from uuid import UUID

from app.domain.ledger.model.budget_overview import BudgetOverviewItem, BudgetOverviewState


class BudgetOverviewQueryRepository(ABC):
    @abstractmethod
    def list_page(
        self,
        timestamp: int,
        states: Collection[BudgetOverviewState],
        account_uuid: UUID | None,
        search: str | None,
        page_size: int,
        cursor_name: str | None,
        cursor_uuid: UUID | None,
    ) -> list[BudgetOverviewItem]:
        pass

    @abstractmethod
    def list_attention(self, timestamp: int, account_uuid: UUID, limit: int) -> list[BudgetOverviewItem]:
        pass
