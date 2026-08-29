from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.ledger.model.cash_flow import CashFlow
from app.domain.ledger.model.transaction_event_filter import TransactionEventFilter


class CashFlowQueryRepository(ABC):
    @abstractmethod
    def get_summary(self, currency_uuid: UUID, filters: TransactionEventFilter) -> CashFlow | None:
        pass

    @abstractmethod
    def list_points(self, currency_uuid: UUID, filters: TransactionEventFilter) -> list[CashFlow]:
        """Return cash flow grouped from caller-provided fixed day boundaries."""
        pass
