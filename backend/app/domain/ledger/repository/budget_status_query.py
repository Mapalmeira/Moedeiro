from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.ledger.model.budget_status import BudgetStatus


class BudgetStatusQueryRepository(ABC):
    @abstractmethod
    def get_status(self, budget_uuid: UUID, timestamp: int) -> BudgetStatus | None:
        pass

    @abstractmethod
    def list_page(self, timestamp: int, page_number: int, page_size: int) -> list[BudgetStatus]:
        pass
