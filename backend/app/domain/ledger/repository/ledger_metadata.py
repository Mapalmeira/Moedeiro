from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.ledger.model.ledger_metadata import LedgerMetadata


class LedgerMetadataRepository(ABC):
    @abstractmethod
    def get(self) -> LedgerMetadata | None:
        pass

    @abstractmethod
    def update_schema_version(self, value: int) -> None:
        pass

    @abstractmethod
    def update_name(self, value: str) -> None:
        pass

    @abstractmethod
    def create(self, ledger_uuid: UUID, name: str, version: int) -> None:
        pass
