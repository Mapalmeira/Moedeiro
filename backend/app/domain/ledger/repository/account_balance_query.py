from abc import ABC, abstractmethod
from uuid import UUID


class AccountBalanceQueryRepository(ABC):
    @abstractmethod
    def get_balance_at(self, account_uuid: UUID, timestamp: int) -> int:
        pass
