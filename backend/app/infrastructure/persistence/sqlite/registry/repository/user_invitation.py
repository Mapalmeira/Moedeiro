import sqlite3
from uuid import UUID, uuid4

from app.domain.registry.model.user_invitation import UserInvitation
from app.domain.registry.repository.user_invitation import UserInvitationRepository


class SqliteUserInvitationRepository(UserInvitationRepository):
    _columns = "uuid, secret_hash, created_at, expires_at, consumed_at"
    _SORT_COLUMNS = {
        "created_at": "created_at",
        "expires_at": "expires_at",
        "consumed_at": "consumed_at",
    }

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, secret_hash: bytes, created_at: int, expires_at: int) -> UserInvitation:
        invitation = UserInvitation(uuid=uuid4(), secret_hash=secret_hash, created_at=created_at, expires_at=expires_at)
        self.connection.execute(
            "INSERT INTO user_invitation(uuid, secret_hash, created_at, expires_at, consumed_at) VALUES (?, ?, ?, ?, ?)",
            (invitation.uuid.bytes, invitation.secret_hash, invitation.created_at, invitation.expires_at, invitation.consumed_at),
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
            "UPDATE user_invitation SET consumed_at = ? WHERE uuid = ? AND consumed_at IS NULL AND created_at <= ? AND expires_at > ?",
            (consumed_at, uuid.bytes, consumed_at, consumed_at),
        )
        return cursor.rowcount == 1

    def delete(self, uuid: UUID) -> bool:
        cursor = self.connection.execute("DELETE FROM user_invitation WHERE uuid = ? AND consumed_at IS NULL", (uuid.bytes,))
        return cursor.rowcount == 1

    def delete_inactive_before(self, timestamp: int) -> int:
        cursor = self.connection.execute("DELETE FROM user_invitation WHERE consumed_at <= ? OR expires_at <= ?", (timestamp, timestamp))
        return cursor.rowcount

    def list_all(self, sort_key: str, ascending: bool) -> list[UserInvitation]:
        sort_column = self._get_sort_column(sort_key)
        direction = "ASC" if ascending else "DESC"
        rows = self.connection.execute(f"SELECT {self._columns} FROM user_invitation ORDER BY {sort_column} {direction}, uuid ASC").fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: sqlite3.Row) -> UserInvitation:
        return UserInvitation.model_validate(dict(row))

    @classmethod
    def _get_sort_column(cls, sort_key: str) -> str:
        try:
            return cls._SORT_COLUMNS[sort_key]
        except KeyError as error:
            raise ValueError(f"Invalid user invitation sort key: {sort_key}") from error
