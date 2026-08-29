import sqlite3
from uuid import UUID, uuid4

from app.domain.registry.model.auth_session import AuthSession, DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, DEFAULT_INACTIVITY_TIMEOUT_SECONDS
from app.domain.registry.repository.auth_session import AuthSessionRepository


class SqliteAuthSessionRepository(AuthSessionRepository):
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, grant_uuid: UUID, token_hash: bytes, created_at: int, inactivity_timeout_seconds: int = DEFAULT_INACTIVITY_TIMEOUT_SECONDS, absolute_timeout_seconds: int = DEFAULT_ABSOLUTE_TIMEOUT_SECONDS) -> AuthSession:
        session = AuthSession(uuid=uuid4(), grant_uuid=grant_uuid, token_hash=token_hash, created_at=created_at, inactivity_timeout_seconds=inactivity_timeout_seconds, absolute_timeout_seconds=absolute_timeout_seconds)
        self.connection.execute(
            "INSERT INTO auth_session(uuid, grant_uuid, token_hash, created_at, inactivity_timeout_seconds, absolute_timeout_seconds, last_activity_at, revoked_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (session.uuid.bytes, session.grant_uuid.bytes, session.token_hash, session.created_at, session.inactivity_timeout_seconds, session.absolute_timeout_seconds, session.last_activity_at, session.revoked_at),
        )
        return session

    def get(self, uuid: UUID) -> AuthSession | None:
        row = self.connection.execute(
            "SELECT uuid, grant_uuid, token_hash, created_at, inactivity_timeout_seconds, absolute_timeout_seconds, last_activity_at, revoked_at FROM auth_session WHERE uuid = ?",
            (uuid.bytes,),
        ).fetchone()
        return None if row is None else self._to_model(row)

    def get_by_token_hash(self, token_hash: bytes) -> AuthSession | None:
        row = self.connection.execute(
            "SELECT uuid, grant_uuid, token_hash, created_at, inactivity_timeout_seconds, absolute_timeout_seconds, last_activity_at, revoked_at FROM auth_session WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()
        return None if row is None else self._to_model(row)

    def update_last_activity(self, uuid: UUID, last_activity_at: int) -> None:
        self.connection.execute(
            "UPDATE auth_session SET last_activity_at = ? WHERE uuid = ? AND revoked_at IS NULL AND created_at <= ? AND created_at + absolute_timeout_seconds > ? AND COALESCE(last_activity_at, created_at) + inactivity_timeout_seconds > ? AND COALESCE(last_activity_at, created_at) <= ?",
            (last_activity_at, uuid.bytes, last_activity_at, last_activity_at, last_activity_at, last_activity_at),
        )

    def revoke(self, uuid: UUID, revoked_at: int) -> None:
        self.connection.execute(
            "UPDATE auth_session SET revoked_at = ? WHERE uuid = ? AND revoked_at IS NULL",
            (revoked_at, uuid.bytes),
        )

    def revoke_by_grant(self, grant_uuid: UUID, revoked_at: int) -> None:
        self.connection.execute(
            "UPDATE auth_session SET revoked_at = ? WHERE grant_uuid = ? AND revoked_at IS NULL",
            (revoked_at, grant_uuid.bytes),
        )

    def list_by_grant(self, grant_uuid: UUID) -> list[AuthSession]:
        rows = self.connection.execute(
            "SELECT uuid, grant_uuid, token_hash, created_at, inactivity_timeout_seconds, absolute_timeout_seconds, last_activity_at, revoked_at FROM auth_session WHERE grant_uuid = ?",
            (grant_uuid.bytes,),
        ).fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: sqlite3.Row) -> AuthSession:
        return AuthSession.model_validate(dict(row))
