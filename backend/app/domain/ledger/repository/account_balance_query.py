from abc import ABC, abstractmethod
from uuid import UUID


class AccountBalanceQueryRepository(ABC):
    @abstractmethod
    def get_balance_at(self, account_uuid: UUID, timestamp: int) -> int:
        """Return the balance through timestamp or raise LookupError if the account does not exist."""
        pass

    @abstractmethod
    def list_points(self, account_uuid: UUID, from_timestamp: int, point_count: int, point_interval: int) -> list[int]:
        """Return closing balances for point_count consecutive intervals.

        Each interval has point_interval seconds and starts at from_timestamp.
        An unknown account raises LookupError.
        """
        pass
