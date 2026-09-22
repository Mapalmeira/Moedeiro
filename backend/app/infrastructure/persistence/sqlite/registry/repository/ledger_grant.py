import sqlite3
from uuid import UUID, uuid4

from app.domain.registry.model.ledger_grant import LedgerGrant, LedgerGrantType
from app.domain.registry.repository.ledger_grant import LedgerGrantRepository


class SqliteLedgerGrantRepository(LedgerGrantRepository):
    _columns = "uuid, user_uuid, ledger_uuid, type, created_at, revoked_at"

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, user_uuid: UUID, ledger_uuid: UUID, type: LedgerGrantType, created_at: int) -> LedgerGrant:
        grant = LedgerGrant(uuid=uuid4(), user_uuid=user_uuid, ledger_uuid=ledger_uuid, type=type, created_at=created_at)
        self.connection.execute(
            "INSERT INTO ledger_grant(uuid, user_uuid, ledger_uuid, type, created_at, revoked_at) VALUES (?, ?, ?, ?, ?, ?)",
            (grant.uuid.bytes, grant.user_uuid.bytes, grant.ledger_uuid.bytes, grant.type, grant.created_at, grant.revoked_at),
        )
        return grant

    def get(self, uuid: UUID) -> LedgerGrant | None:
        row = self.connection.execute(f"SELECT {self._columns} FROM ledger_grant WHERE uuid = ?", (uuid.bytes,)).fetchone()
        return None if row is None else self._to_model(row)

    def get_active_owner(self, user_uuid: UUID, ledger_uuid: UUID) -> LedgerGrant | None:
        row = self.connection.execute(
            f"SELECT {self._columns} FROM ledger_grant WHERE user_uuid = ? AND ledger_uuid = ? AND type = 'OWNER' AND revoked_at IS NULL",
            (user_uuid.bytes, ledger_uuid.bytes),
        ).fetchone()
        return None if row is None else self._to_model(row)

    def revoke(self, uuid: UUID, revoked_at: int) -> None:
        self.connection.execute("UPDATE ledger_grant SET revoked_at = ? WHERE uuid = ? AND revoked_at IS NULL", (revoked_at, uuid.bytes))

    def delete_inactive_before(self, timestamp: int) -> int:
        cursor = self.connection.execute("DELETE FROM ledger_grant WHERE revoked_at <= ?", (timestamp,))
        return cursor.rowcount

    def list_by_user(self, user_uuid: UUID) -> list[LedgerGrant]:
        rows = self.connection.execute(f"SELECT {self._columns} FROM ledger_grant WHERE user_uuid = ?", (user_uuid.bytes,)).fetchall()
        return [self._to_model(row) for row in rows]

    def list_by_ledger(self, ledger_uuid: UUID) -> list[LedgerGrant]:
        rows = self.connection.execute(f"SELECT {self._columns} FROM ledger_grant WHERE ledger_uuid = ?", (ledger_uuid.bytes,)).fetchall()
        return [self._to_model(row) for row in rows]

    def list_all(self) -> list[LedgerGrant]:
        rows = self.connection.execute(f"SELECT {self._columns} FROM ledger_grant ORDER BY created_at ASC, uuid ASC").fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: sqlite3.Row) -> LedgerGrant:
        return LedgerGrant.model_validate(dict(row))
