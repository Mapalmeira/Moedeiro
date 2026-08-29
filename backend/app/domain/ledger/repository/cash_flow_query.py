from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.ledger.model.cash_flow import CashFlow
from app.domain.ledger.model.financial_event_filter import FinancialEventFilter


class CashFlowQueryRepository(ABC):
    @abstractmethod
    def get_summary(self, currency_uuid: UUID, filters: FinancialEventFilter) -> CashFlow:
        pass

    @abstractmethod
    def list_points(self, currency_uuid: UUID, filters: FinancialEventFilter) -> list[CashFlow]:
        """Return cash flow for consecutive fixed 24-hour intervals.

        The filter's from_timestamp must be the first day boundary and the filter's
        to_timestamp the exclusive boundary after the last day. Item i belongs to the
        interval starting at from_timestamp + i * 86400.
        """
        pass
