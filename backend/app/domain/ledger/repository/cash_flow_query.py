from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.ledger.model.cash_flow import CashFlow
from app.domain.ledger.model.financial_event_filter import FinancialEventFilter


class CashFlowQueryRepository(ABC):
    @abstractmethod
    def get_summary(self, currency_uuid: UUID, filters: FinancialEventFilter) -> CashFlow:
        pass

    @abstractmethod
    def list_points(self, currency_uuid: UUID, filters: FinancialEventFilter, point_width: int) -> list[CashFlow]:
        """Return cash flow for consecutive intervals of point_width seconds.

        The final point covers the remaining portion of the filter interval when it
        is narrower than point_width.
        """
        pass
