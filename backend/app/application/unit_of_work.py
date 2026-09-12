"""Abstract transactional wrapper contract.

Changes require an explicit commit. Leaving the scope rolls back pending changes
and closes the resources owned by the unit of work.
"""

from abc import ABC, abstractmethod

from typing_extensions import Self


class UnitOfWork(ABC):
    @abstractmethod
    def __enter__(self) -> Self:
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        pass

    @abstractmethod
    def commit(self) -> None:
        pass

    @abstractmethod
    def rollback(self) -> None:
        pass
