import sqlite3
from uuid import UUID, uuid4

from app.domain.registry.model.remember_session import DEFAULT_EXPIRATION_TIMEOUT_SECONDS, RememberSession
from app.domain.registry.repository.remember_session import RememberSessionRepository


class SqliteRememberSessionRepository(RememberSessionRepository):
    _columns = "uuid, user_uuid, token_hash, created_at, expiration_timeout_seconds, last_used_at, revoked_at"
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, user_uuid: UUID, token_hash: bytes, created_at: int, expiration_timeout_seconds: int = DEFAULT_EXPIRATION_TIMEOUT_SECONDS) -> RememberSession:
        session = RememberSession(uuid=uuid4(), user_uuid=user_uuid, token_hash=token_hash, created_at=created_at, expiration_timeout_seconds=expiration_timeout_seconds)
        self.connection.execute(
            "INSERT INTO remember_session(uuid, user_uuid, token_hash, created_at, expiration_timeout_seconds, last_used_at, revoked_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session.uuid.bytes, session.user_uuid.bytes, session.token_hash, session.created_at, session.expiration_timeout_seconds, session.last_used_at, session.revoked_at),
        )
        return session

    def get(self, uuid: UUID) -> RememberSession | None:
        row = self.connection.execute(f"SELECT {self._columns} FROM remember_session WHERE uuid = ?", (uuid.bytes,)).fetchone()
        return None if row is None else self._to_model(row)

    def get_by_token_hash(self, token_hash: bytes) -> RememberSession | None:
        row = self.connection.execute(f"SELECT {self._columns} FROM remember_session WHERE token_hash = ?", (token_hash,)).fetchone()
        return None if row is None else self._to_model(row)

    def rotate(self, uuid: UUID, token_hash: bytes, last_used_at: int) -> bool:
        cursor = self.connection.execute(
            "UPDATE remember_session SET token_hash = ?, last_used_at = ? WHERE uuid = ? AND revoked_at IS NULL AND created_at <= ? AND created_at + expiration_timeout_seconds > ? AND COALESCE(last_used_at, created_at) <= ?",
            (token_hash, last_used_at, uuid.bytes, last_used_at, last_used_at, last_used_at),
        )
        return cursor.rowcount == 1

    def revoke(self, uuid: UUID, revoked_at: int) -> None:
        self.connection.execute("UPDATE remember_session SET revoked_at = ? WHERE uuid = ? AND revoked_at IS NULL", (revoked_at, uuid.bytes))

    def revoke_by_user(self, user_uuid: UUID, revoked_at: int) -> None:
        self.connection.execute("UPDATE remember_session SET revoked_at = ? WHERE user_uuid = ? AND revoked_at IS NULL", (revoked_at, user_uuid.bytes))

    def list_by_user(self, user_uuid: UUID) -> list[RememberSession]:
        rows = self.connection.execute(f"SELECT {self._columns} FROM remember_session WHERE user_uuid = ?", (user_uuid.bytes,)).fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: sqlite3.Row) -> RememberSession:
        return RememberSession.model_validate(dict(row))
