from abc import ABC, abstractmethod
from typing import Self


class UnitOfWork(ABC):
    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.rollback()

    @abstractmethod
    def commit(self) -> None:
        pass

    @abstractmethod
    def rollback(self) -> None:
        pass
