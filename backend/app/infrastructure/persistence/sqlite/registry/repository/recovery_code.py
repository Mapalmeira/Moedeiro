import sqlite3
from uuid import UUID, uuid4

from app.domain.registry.model.recovery_code import RecoveryCode
from app.domain.registry.repository.recovery_code import RecoveryCodeRepository


class SqliteRecoveryCodeRepository(RecoveryCodeRepository):
    _columns = "uuid, user_uuid, code_hash, created_at, used_at, revoked_at"

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, user_uuid: UUID, code_hash: bytes, created_at: int) -> RecoveryCode:
        recovery_code = RecoveryCode(uuid=uuid4(), user_uuid=user_uuid, code_hash=code_hash, created_at=created_at)
        self.connection.execute(
            "INSERT INTO recovery_code(uuid, user_uuid, code_hash, created_at, used_at, revoked_at) VALUES (?, ?, ?, ?, ?, ?)",
            (recovery_code.uuid.bytes, recovery_code.user_uuid.bytes, recovery_code.code_hash, recovery_code.created_at, recovery_code.used_at, recovery_code.revoked_at),
        )
        return recovery_code

    def get(self, uuid: UUID) -> RecoveryCode | None:
        row = self.connection.execute(f"SELECT {self._columns} FROM recovery_code WHERE uuid = ?", (uuid.bytes,)).fetchone()
        return None if row is None else self._to_model(row)

    def get_by_code_hash(self, code_hash: bytes) -> RecoveryCode | None:
        row = self.connection.execute(f"SELECT {self._columns} FROM recovery_code WHERE code_hash = ?", (code_hash,)).fetchone()
        return None if row is None else self._to_model(row)

    def consume(self, uuid: UUID, used_at: int) -> bool:
        cursor = self.connection.execute("UPDATE recovery_code SET used_at = ? WHERE uuid = ? AND used_at IS NULL AND revoked_at IS NULL AND created_at <= ?", (used_at, uuid.bytes, used_at))
        return cursor.rowcount == 1

    def revoke(self, uuid: UUID, revoked_at: int) -> None:
        self.connection.execute("UPDATE recovery_code SET revoked_at = ? WHERE uuid = ? AND used_at IS NULL AND revoked_at IS NULL AND created_at <= ?", (revoked_at, uuid.bytes, revoked_at))

    def delete_revoked_before(self, timestamp: int) -> int:
        cursor = self.connection.execute("DELETE FROM recovery_code WHERE revoked_at <= ?", (timestamp,))
        return cursor.rowcount

    def list_by_user(self, user_uuid: UUID) -> list[RecoveryCode]:
        rows = self.connection.execute(f"SELECT {self._columns} FROM recovery_code WHERE user_uuid = ?", (user_uuid.bytes,)).fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: sqlite3.Row) -> RecoveryCode:
        return RecoveryCode.model_validate(dict(row))
