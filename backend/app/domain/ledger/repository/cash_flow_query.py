from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.ledger.model.cash_flow import CashFlow
from app.domain.ledger.model.cash_flow_sankey import CashFlowCategoryTotal
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

    @abstractmethod
    def list_category_totals(self, currency_uuid: UUID, filters: FinancialEventFilter) -> list[CashFlowCategoryTotal]:
        """Aggregate cash-flow movements by category for one currency.

        Transfer events follow the cash-flow summary contract: they are excluded
        for currency-wide results and the selected account side is included when
        account_uuid is present in filters.
        """
        pass
