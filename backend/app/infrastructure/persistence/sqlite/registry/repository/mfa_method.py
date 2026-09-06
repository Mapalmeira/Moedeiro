import sqlite3
from uuid import UUID, uuid4

from app.domain.registry.model.mfa_method import MfaMethod, MfaMethodType, TOTP_SETUP_TTL_SECONDS
from app.domain.registry.repository.mfa_method import MfaMethodRepository


class SqliteMfaMethodRepository(MfaMethodRepository):
    _columns = "uuid, user_uuid, type, secret_encrypted, created_at, confirmed_at, last_used_counter"

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, user_uuid: UUID, type: MfaMethodType, secret_encrypted: bytes, created_at: int, confirmed_at: int | None = None, last_used_counter: int | None = None) -> MfaMethod:
        method = MfaMethod(uuid=uuid4(), user_uuid=user_uuid, type=type, secret_encrypted=secret_encrypted, created_at=created_at, confirmed_at=confirmed_at, last_used_counter=last_used_counter)
        self.connection.execute(
            "INSERT INTO mfa_method(uuid, user_uuid, type, secret_encrypted, created_at, confirmed_at, last_used_counter) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (method.uuid.bytes, method.user_uuid.bytes, method.type, method.secret_encrypted, method.created_at, method.confirmed_at, method.last_used_counter),
        )
        return method

    def get(self, uuid: UUID) -> MfaMethod | None:
        row = self.connection.execute(f"SELECT {self._columns} FROM mfa_method WHERE uuid = ?", (uuid.bytes,)).fetchone()
        return None if row is None else self._to_model(row)

    def get_totp_by_user(self, user_uuid: UUID) -> MfaMethod | None:
        row = self.connection.execute(f"SELECT {self._columns} FROM mfa_method WHERE user_uuid = ? AND type = 'TOTP'", (user_uuid.bytes,)).fetchone()
        return None if row is None else self._to_model(row)

    def is_totp_enabled(self, user_uuid: UUID) -> bool:
        row = self.connection.execute(
            "SELECT EXISTS(SELECT 1 FROM mfa_method WHERE user_uuid = ? AND type = 'TOTP' AND confirmed_at IS NOT NULL)",
            (user_uuid.bytes,),
        ).fetchone()
        return bool(row[0])

    def confirm(self, uuid: UUID, confirmed_at: int, last_used_counter: int) -> bool:
        cursor = self.connection.execute("UPDATE mfa_method SET confirmed_at = ?, last_used_counter = ? WHERE uuid = ? AND confirmed_at IS NULL AND created_at <= ? AND created_at > ?", (confirmed_at, last_used_counter, uuid.bytes, confirmed_at, confirmed_at - TOTP_SETUP_TTL_SECONDS))
        return cursor.rowcount == 1

    def use_totp_counter(self, uuid: UUID, counter: int) -> bool:
        cursor = self.connection.execute(
            "UPDATE mfa_method SET last_used_counter = ? WHERE uuid = ? AND confirmed_at IS NOT NULL AND (last_used_counter IS NULL OR last_used_counter < ?)",
            (counter, uuid.bytes, counter),
        )
        return cursor.rowcount == 1

    def delete_unconfirmed_before(self, timestamp: int) -> int:
        cursor = self.connection.execute("DELETE FROM mfa_method WHERE confirmed_at IS NULL AND created_at <= ?", (timestamp,))
        return cursor.rowcount

    def delete(self, uuid: UUID) -> None:
        self.connection.execute("DELETE FROM mfa_method WHERE uuid = ?", (uuid.bytes,))

    def list_by_user(self, user_uuid: UUID) -> list[MfaMethod]:
        rows = self.connection.execute(f"SELECT {self._columns} FROM mfa_method WHERE user_uuid = ?", (user_uuid.bytes,)).fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: sqlite3.Row) -> MfaMethod:
        return MfaMethod.model_validate(dict(row))
