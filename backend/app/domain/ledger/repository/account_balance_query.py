from abc import ABC, abstractmethod
from uuid import UUID


class AccountBalanceQueryRepository(ABC):
    @abstractmethod
    def get_balance_at(self, account_uuid: UUID, timestamp: int) -> int:
        """Return the balance through timestamp or raise LookupError if the account does not exist."""
        pass

    @abstractmethod
    def get_currency_balance_at(self, currency_uuid: UUID, timestamp: int) -> int:
        """Return the aggregate balance for every account in a currency through timestamp."""
        pass

    @abstractmethod
    def list_balances_at(
        self,
        timestamp: int,
        currency_uuid: UUID | None = None,
        limit: int | None = None,
    ) -> list[tuple[UUID, UUID, int]]:
        """Return account UUID, currency UUID and balance through timestamp.

        When currency_uuid is provided, only accounts in that currency are returned.
        When limit is provided, account selection is limited before balances are aggregated.
        """
        pass

    @abstractmethod
    def list_points(self, account_uuid: UUID, from_timestamp: int, point_count: int, point_interval: int) -> list[int]:
        """Return closing balances for point_count consecutive intervals.

        Each interval has point_interval seconds and starts at from_timestamp.
        An unknown account raises LookupError.
        """
        pass
