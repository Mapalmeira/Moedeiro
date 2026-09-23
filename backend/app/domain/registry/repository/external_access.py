from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.external_access import ExternalAccess


class ExternalAccessRepository(ABC):
    @abstractmethod
    def create(self, name: str, token_hash: bytes) -> ExternalAccess:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> ExternalAccess | None:
        pass

    @abstractmethod
    def get_by_token_hash(self, token_hash: bytes) -> ExternalAccess | None:
        pass

    @abstractmethod
    def list_all(self) -> list[ExternalAccess]:
        pass

    @abstractmethod
    def delete(self, uuid: UUID) -> bool:
        pass

    @abstractmethod
    def delete_ungranted(self) -> int:
        pass
