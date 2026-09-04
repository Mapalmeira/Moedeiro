import sqlite3
from uuid import UUID, uuid4

from app.domain.registry.model.auth_session import AuthSession
from app.domain.registry.repository.auth_session import AuthSessionRepository


class SqliteAuthSessionRepository(AuthSessionRepository):
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, user_uuid: UUID, token_hash: bytes, created_at: int, expires_at: int, inactivity_timeout_seconds: int) -> AuthSession:
        session = AuthSession(uuid=uuid4(), user_uuid=user_uuid, token_hash=token_hash, created_at=created_at, expires_at=expires_at, inactivity_timeout_seconds=inactivity_timeout_seconds)
        self.connection.execute(
            "INSERT INTO auth_session(uuid, user_uuid, token_hash, created_at, expires_at, inactivity_timeout_seconds, last_activity_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session.uuid.bytes, session.user_uuid.bytes, session.token_hash, session.created_at, session.expires_at, session.inactivity_timeout_seconds, session.last_activity_at),
        )
        return session

    def get(self, uuid: UUID) -> AuthSession | None:
        row = self.connection.execute(
            "SELECT uuid, user_uuid, token_hash, created_at, expires_at, inactivity_timeout_seconds, last_activity_at FROM auth_session WHERE uuid = ?",
            (uuid.bytes,),
        ).fetchone()
        return None if row is None else self._to_model(row)

    def get_by_token_hash(self, token_hash: bytes) -> AuthSession | None:
        row = self.connection.execute(
            "SELECT uuid, user_uuid, token_hash, created_at, expires_at, inactivity_timeout_seconds, last_activity_at FROM auth_session WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()
        return None if row is None else self._to_model(row)

    def get_active_by_token_hash(self, token_hash: bytes, timestamp: int) -> AuthSession | None:
        row = self.connection.execute(
            "SELECT uuid, user_uuid, token_hash, created_at, expires_at, inactivity_timeout_seconds, last_activity_at FROM auth_session WHERE token_hash = ? AND created_at <= ? AND expires_at > ? AND COALESCE(last_activity_at, created_at) + inactivity_timeout_seconds > ?",
            (token_hash, timestamp, timestamp, timestamp),
        ).fetchone()
        return None if row is None else self._to_model(row)

    def update_last_activity(self, uuid: UUID, last_activity_at: int) -> bool:
        cursor = self.connection.execute(
            "UPDATE auth_session SET last_activity_at = ? WHERE uuid = ? AND created_at <= ? AND expires_at > ? AND COALESCE(last_activity_at, created_at) + inactivity_timeout_seconds > ? AND COALESCE(last_activity_at, created_at) <= ?",
            (last_activity_at, uuid.bytes, last_activity_at, last_activity_at, last_activity_at, last_activity_at),
        )
        return cursor.rowcount == 1

    def delete(self, uuid: UUID) -> None:
        self.connection.execute("DELETE FROM auth_session WHERE uuid = ?", (uuid.bytes,))

    def delete_by_user(self, user_uuid: UUID) -> None:
        self.connection.execute("DELETE FROM auth_session WHERE user_uuid = ?", (user_uuid.bytes,))

    def delete_inactive_before(self, timestamp: int) -> int:
        cursor = self.connection.execute("DELETE FROM auth_session WHERE expires_at <= ? OR COALESCE(last_activity_at, created_at) + inactivity_timeout_seconds <= ?", (timestamp, timestamp))
        return cursor.rowcount

    def list_by_user(self, user_uuid: UUID) -> list[AuthSession]:
        rows = self.connection.execute(
            "SELECT uuid, user_uuid, token_hash, created_at, expires_at, inactivity_timeout_seconds, last_activity_at FROM auth_session WHERE user_uuid = ?",
            (user_uuid.bytes,),
        ).fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: sqlite3.Row) -> AuthSession:
        return AuthSession.model_validate(dict(row))
