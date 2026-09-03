from abc import ABC, abstractmethod

from app.domain.registry.model.registry_metadata import RegistryMetadata


class RegistryMetadataRepository(ABC):
    @abstractmethod
    def get(self) -> RegistryMetadata | None:
        pass

    @abstractmethod
    def create(self, schema_version: int) -> RegistryMetadata:
        pass

    @abstractmethod
    def update_schema_version(self, value: int) -> None:
        pass
