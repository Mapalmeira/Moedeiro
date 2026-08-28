from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from typing import Generic, TypeVar


ConnectionT = TypeVar("ConnectionT")


class Database(ABC, Generic[ConnectionT]):
    @abstractmethod
    def connection(self) -> AbstractContextManager[ConnectionT]:
        pass
