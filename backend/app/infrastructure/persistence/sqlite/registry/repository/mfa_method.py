import sqlite3
from uuid import UUID, uuid4

from app.domain.registry.model.mfa_method import MfaMethod, MfaMethodType
from app.domain.registry.repository.mfa_method import MfaMethodRepository


class SqliteMfaMethodRepository(MfaMethodRepository):
    _columns = "uuid, user_uuid, type, secret_encrypted, created_at"

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, user_uuid: UUID, type: MfaMethodType, secret_encrypted: bytes, created_at: int) -> MfaMethod:
        method = MfaMethod(uuid=uuid4(), user_uuid=user_uuid, type=type, secret_encrypted=secret_encrypted, created_at=created_at)
        self.connection.execute(
            "INSERT INTO mfa_method(uuid, user_uuid, type, secret_encrypted, created_at) VALUES (?, ?, ?, ?, ?)",
            (method.uuid.bytes, method.user_uuid.bytes, method.type, method.secret_encrypted, method.created_at),
        )
        return method

    def get(self, uuid: UUID) -> MfaMethod | None:
        row = self.connection.execute(f"SELECT {self._columns} FROM mfa_method WHERE uuid = ?", (uuid.bytes,)).fetchone()
        return None if row is None else self._to_model(row)

    def delete(self, uuid: UUID) -> None:
        self.connection.execute("DELETE FROM mfa_method WHERE uuid = ?", (uuid.bytes,))

    def list_by_user(self, user_uuid: UUID) -> list[MfaMethod]:
        rows = self.connection.execute(f"SELECT {self._columns} FROM mfa_method WHERE user_uuid = ?", (user_uuid.bytes,)).fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: sqlite3.Row) -> MfaMethod:
        return MfaMethod.model_validate(dict(row))
