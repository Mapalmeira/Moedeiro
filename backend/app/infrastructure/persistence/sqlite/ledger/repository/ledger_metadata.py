import sqlite3
from time import time
from uuid import UUID

from app.domain.ledger.model.ledger_metadata import LedgerMetadata
from app.domain.ledger.repository.ledger_metadata import LedgerMetadataRepository


class SqliteLedgerMetadataRepository(LedgerMetadataRepository):
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def get(self) -> LedgerMetadata | None:
        row = self.connection.execute(
            "SELECT ledger_uuid, schema_version, revision, created_at FROM ledger_metadata WHERE singleton = 1"
        ).fetchone()
        if row is None:
            return None
        return LedgerMetadata.model_validate(dict(row))

    def update_schema_version(self, value: int) -> None:
        metadata = LedgerMetadata(ledger_uuid=UUID(int=0), schema_version=value, revision=0, created_at=0)
        self.connection.execute(
            "UPDATE ledger_metadata SET schema_version = ? WHERE singleton = 1",
            (metadata.schema_version,),
        )

    def create(self, ledger_uuid: UUID, version: int) -> LedgerMetadata:
        metadata = LedgerMetadata(
            ledger_uuid=ledger_uuid,
            schema_version=version,
            revision=0,
            created_at=int(time()),
        )
        self.connection.execute(
            """
            INSERT INTO ledger_metadata(singleton, ledger_uuid, schema_version, revision, created_at)
            VALUES (1, ?, ?, ?, ?)
            """,
            (
                metadata.ledger_uuid.bytes,
                metadata.schema_version,
                metadata.revision,
                metadata.created_at,
            ),
        )
        return metadata
