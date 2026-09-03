import sqlite3

from app.domain.registry.model.registry_metadata import RegistryMetadata
from app.domain.registry.repository.registry_metadata import RegistryMetadataRepository


class SqliteRegistryMetadataRepository(RegistryMetadataRepository):
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def get(self) -> RegistryMetadata | None:
        row = self.connection.execute(
            "SELECT schema_version FROM registry_metadata WHERE singleton = 1"
        ).fetchone()
        return None if row is None else RegistryMetadata.model_validate(dict(row))

    def create(self, schema_version: int) -> RegistryMetadata:
        metadata = RegistryMetadata(schema_version=schema_version)
        self.connection.execute(
            "INSERT INTO registry_metadata(singleton, schema_version) VALUES (1, ?)",
            (metadata.schema_version,),
        )
        return metadata

    def update_schema_version(self, value: int) -> None:
        metadata = RegistryMetadata(schema_version=value)
        self.connection.execute(
            "UPDATE registry_metadata SET schema_version = ? WHERE singleton = 1",
            (metadata.schema_version,),
        )
