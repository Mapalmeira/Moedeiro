import sqlite3
from uuid import UUID, uuid4

from app.domain.registry.model.ledger_grant import LedgerGrant, LedgerRole
from app.domain.registry.repository.ledger_grant import LedgerGrantRepository


class SqliteLedgerGrantRepository(LedgerGrantRepository):
    _columns = "uuid, grantee_uuid, ledger_uuid, role, created_at, revoked_at"

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, grantee_uuid: UUID, ledger_uuid: UUID, role: LedgerRole, created_at: int) -> LedgerGrant:
        grant = LedgerGrant(
            uuid=uuid4(),
            grantee_uuid=grantee_uuid,
            ledger_uuid=ledger_uuid,
            role=role,
            created_at=created_at,
        )
        self.connection.execute(
            "INSERT INTO ledger_grant(uuid, grantee_uuid, ledger_uuid, role, created_at, revoked_at) VALUES (?, ?, ?, ?, ?, NULL)",
            (grant.uuid.bytes, grant.grantee_uuid.bytes, grant.ledger_uuid.bytes, grant.role, grant.created_at),
        )
        return grant

    def get(self, uuid: UUID) -> LedgerGrant | None:
        row = self.connection.execute(f"SELECT {self._columns} FROM ledger_grant WHERE uuid = ?", (uuid.bytes,)).fetchone()
        return None if row is None else self._to_model(row)

    def get_active_owner(self, user_uuid: UUID, ledger_uuid: UUID) -> LedgerGrant | None:
        row = self.connection.execute(
            f"""
            SELECT {self._columns}
            FROM ledger_grant
            WHERE grantee_uuid = ?
              AND ledger_uuid = ?
              AND role = 'OWNER'
              AND revoked_at IS NULL
            """,
            (user_uuid.bytes, ledger_uuid.bytes),
        ).fetchone()
        return None if row is None else self._to_model(row)

    def get_active_owner_by_ledger(self, ledger_uuid: UUID) -> LedgerGrant | None:
        row = self.connection.execute(
            f"""
            SELECT {self._columns}
            FROM ledger_grant
            WHERE ledger_uuid = ?
              AND role = 'OWNER'
              AND revoked_at IS NULL
            """,
            (ledger_uuid.bytes,),
        ).fetchone()
        return None if row is None else self._to_model(row)

    def revoke(self, uuid: UUID, revoked_at: int) -> None:
        self.connection.execute("UPDATE ledger_grant SET revoked_at = ? WHERE uuid = ? AND revoked_at IS NULL", (revoked_at, uuid.bytes))

    def revoke_active_guests_by_ledger_and_role(self, ledger_uuid: UUID, role: LedgerRole, revoked_at: int) -> None:
        self.connection.execute(
            """
            UPDATE ledger_grant
            SET revoked_at = ?
            WHERE ledger_uuid = ?
              AND role = ?
              AND revoked_at IS NULL
            """,
            (revoked_at, ledger_uuid.bytes, role),
        )

    def delete_inactive_before(self, timestamp: int) -> int:
        cursor = self.connection.execute("DELETE FROM ledger_grant WHERE revoked_at <= ?", (timestamp,))
        return cursor.rowcount

    def list_by_grantee(self, grantee_uuid: UUID) -> list[LedgerGrant]:
        rows = self.connection.execute(
            f"SELECT {self._columns} FROM ledger_grant WHERE grantee_uuid = ? ORDER BY created_at ASC, uuid ASC",
            (grantee_uuid.bytes,),
        ).fetchall()
        return [self._to_model(row) for row in rows]

    def list_by_grantee_and_ledger(self, grantee_uuid: UUID, ledger_uuid: UUID) -> list[LedgerGrant]:
        rows = self.connection.execute(
            f"SELECT {self._columns} FROM ledger_grant WHERE grantee_uuid = ? AND ledger_uuid = ? ORDER BY created_at ASC, uuid ASC",
            (grantee_uuid.bytes, ledger_uuid.bytes),
        ).fetchall()
        return [self._to_model(row) for row in rows]

    def list_by_ledger(self, ledger_uuid: UUID) -> list[LedgerGrant]:
        rows = self.connection.execute(
            f"SELECT {self._columns} FROM ledger_grant WHERE ledger_uuid = ? ORDER BY created_at ASC, uuid ASC",
            (ledger_uuid.bytes,),
        ).fetchall()
        return [self._to_model(row) for row in rows]

    def list_all(self) -> list[LedgerGrant]:
        rows = self.connection.execute(f"SELECT {self._columns} FROM ledger_grant ORDER BY created_at ASC, uuid ASC").fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: sqlite3.Row) -> LedgerGrant:
        return LedgerGrant.model_validate(dict(row))
