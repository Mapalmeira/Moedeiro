from abc import ABC, abstractmethod

from app.domain.ledger.model.cash_flow import CashFlow
from app.domain.ledger.model.transaction_event_filter import TransactionEventFilter


class CashFlowQueryRepository(ABC):
    @abstractmethod
    def get_summary(self, filters: TransactionEventFilter) -> CashFlow:
        pass

    @abstractmethod
    def list_points(self, filters: TransactionEventFilter) -> list[CashFlow]:
        """Return the filtered cash flow grouped into daily intervals."""
        pass
