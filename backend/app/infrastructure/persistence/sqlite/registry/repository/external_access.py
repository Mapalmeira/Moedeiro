import sqlite3
from uuid import UUID, uuid4

from app.domain.registry.model.external_access import ExternalAccess
from app.domain.registry.repository.external_access import ExternalAccessRepository


class SqliteExternalAccessRepository(ExternalAccessRepository):
    _columns = "uuid, user_uuid, name, token_hash"

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, user_uuid: UUID, name: str, token_hash: bytes) -> ExternalAccess:
        access = ExternalAccess(uuid=uuid4(), user_uuid=user_uuid, name=name, token_hash=token_hash)
        self.connection.execute("INSERT INTO ledger_grantee(uuid) VALUES (?)", (access.uuid.bytes,))
        try:
            self.connection.execute(
                "INSERT INTO external_access(uuid, user_uuid, name, token_hash) VALUES (?, ?, ?, ?)",
                (access.uuid.bytes, access.user_uuid.bytes, access.name, access.token_hash),
            )
        except sqlite3.Error:
            self.connection.execute("DELETE FROM ledger_grantee WHERE uuid = ?", (access.uuid.bytes,))
            raise
        return access

    def get(self, uuid: UUID) -> ExternalAccess | None:
        row = self.connection.execute(f"SELECT {self._columns} FROM external_access WHERE uuid = ?", (uuid.bytes,)).fetchone()
        return None if row is None else self._to_model(row)

    def get_by_token_hash(self, token_hash: bytes) -> ExternalAccess | None:
        row = self.connection.execute(f"SELECT {self._columns} FROM external_access WHERE token_hash = ?", (token_hash,)).fetchone()
        return None if row is None else self._to_model(row)

    def list_by_user(self, user_uuid: UUID) -> list[ExternalAccess]:
        rows = self.connection.execute(
            f"SELECT {self._columns} FROM external_access WHERE user_uuid = ? ORDER BY name ASC, uuid ASC",
            (user_uuid.bytes,),
        ).fetchall()
        return [self._to_model(row) for row in rows]

    def delete(self, uuid: UUID) -> bool:
        cursor = self.connection.execute(
            "DELETE FROM ledger_grantee WHERE uuid = ? AND EXISTS (SELECT 1 FROM external_access WHERE uuid = ?)",
            (uuid.bytes, uuid.bytes),
        )
        return cursor.rowcount == 1

    def delete_ungranted(self) -> int:
        cursor = self.connection.execute(
            """
            DELETE FROM ledger_grantee
            WHERE uuid IN (
                SELECT external_access.uuid
                FROM external_access
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM ledger_grant
                    WHERE ledger_grant.grantee_uuid = external_access.uuid
                )
            )
            """
        )
        return cursor.rowcount

    @staticmethod
    def _to_model(row: sqlite3.Row) -> ExternalAccess:
        return ExternalAccess.model_validate(dict(row))
