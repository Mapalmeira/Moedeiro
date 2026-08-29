from abc import ABC, abstractmethod
from uuid import UUID


class AccountBalanceQueryRepository(ABC):
    @abstractmethod
    def get_balance_at(self, account_uuid: UUID, timestamp: int) -> int:
        """Return the balance through timestamp or raise LookupError if the account does not exist."""
        pass

    @abstractmethod
    def list_points(self, account_uuid: UUID, from_timestamp: int, to_timestamp: int) -> list[int]:
        """Return balances for consecutive fixed 24-hour intervals.

        from_timestamp must be the first day boundary and to_timestamp the
        exclusive boundary after the last day. Item i belongs to the interval
        starting at from_timestamp + i * 86400. An unknown account raises
        LookupError.
        """
        pass
