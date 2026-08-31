import sqlite3
from uuid import UUID, uuid4

from app.domain.registry.model.user_invitation import DEFAULT_EXPIRATION_TIMEOUT_SECONDS, UserInvitation
from app.domain.registry.repository.user_invitation import UserInvitationRepository


class SqliteUserInvitationRepository(UserInvitationRepository):
    _columns = "uuid, secret_hash, created_at, expiration_timeout_seconds, consumed_at, revoked_at"

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, secret_hash: bytes, created_at: int, expiration_timeout_seconds: int = DEFAULT_EXPIRATION_TIMEOUT_SECONDS) -> UserInvitation:
        invitation = UserInvitation(uuid=uuid4(), secret_hash=secret_hash, created_at=created_at, expiration_timeout_seconds=expiration_timeout_seconds)
        self.connection.execute(
            "INSERT INTO user_invitation(uuid, secret_hash, created_at, expiration_timeout_seconds, consumed_at, revoked_at) VALUES (?, ?, ?, ?, ?, ?)",
            (invitation.uuid.bytes, invitation.secret_hash, invitation.created_at, invitation.expiration_timeout_seconds, invitation.consumed_at, invitation.revoked_at),
        )
        return invitation

    def get(self, uuid: UUID) -> UserInvitation | None:
        row = self.connection.execute(f"SELECT {self._columns} FROM user_invitation WHERE uuid = ?", (uuid.bytes,)).fetchone()
        return None if row is None else self._to_model(row)

    def get_by_secret_hash(self, secret_hash: bytes) -> UserInvitation | None:
        row = self.connection.execute(f"SELECT {self._columns} FROM user_invitation WHERE secret_hash = ?", (secret_hash,)).fetchone()
        return None if row is None else self._to_model(row)

    def consume(self, uuid: UUID, consumed_at: int) -> bool:
        cursor = self.connection.execute(
            "UPDATE user_invitation SET consumed_at = ? WHERE uuid = ? AND consumed_at IS NULL AND revoked_at IS NULL AND created_at <= ? AND created_at + expiration_timeout_seconds > ?",
            (consumed_at, uuid.bytes, consumed_at, consumed_at),
        )
        return cursor.rowcount == 1

    def revoke(self, uuid: UUID, revoked_at: int) -> None:
        self.connection.execute(
            "UPDATE user_invitation SET revoked_at = ? WHERE uuid = ? AND consumed_at IS NULL AND revoked_at IS NULL",
            (revoked_at, uuid.bytes),
        )

    def list_all(self) -> list[UserInvitation]:
        rows = self.connection.execute(f"SELECT {self._columns} FROM user_invitation").fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: sqlite3.Row) -> UserInvitation:
        return UserInvitation.model_validate(dict(row))
