import sqlite3
from uuid import UUID, uuid4

from app.domain.registry.model.access_invitation import AccessInvitation
from app.domain.registry.repository.access_invitation import AccessInvitationRepository


class SqliteAccessInvitationRepository(AccessInvitationRepository):
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, ledger_uuid: UUID, secret_hash: bytes, created_at: int, expires_at: int) -> AccessInvitation:
        invitation = AccessInvitation(uuid=uuid4(), ledger_uuid=ledger_uuid, grant_uuid=uuid4(), secret_hash=secret_hash, created_at=created_at, expires_at=expires_at)
        self.connection.execute(
            "INSERT INTO access_invitation(uuid, ledger_uuid, grant_uuid, secret_hash, created_at, expires_at, consumed_at, revoked_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (invitation.uuid.bytes, invitation.ledger_uuid.bytes, invitation.grant_uuid.bytes, invitation.secret_hash, invitation.created_at, invitation.expires_at, invitation.consumed_at, invitation.revoked_at),
        )
        return invitation

    def get(self, uuid: UUID) -> AccessInvitation | None:
        row = self.connection.execute(
            "SELECT uuid, ledger_uuid, grant_uuid, secret_hash, created_at, expires_at, consumed_at, revoked_at FROM access_invitation WHERE uuid = ?",
            (uuid.bytes,),
        ).fetchone()
        return None if row is None else self._to_model(row)

    def get_by_secret_hash(self, secret_hash: bytes) -> AccessInvitation | None:
        row = self.connection.execute(
            "SELECT uuid, ledger_uuid, grant_uuid, secret_hash, created_at, expires_at, consumed_at, revoked_at FROM access_invitation WHERE secret_hash = ?",
            (secret_hash,),
        ).fetchone()
        return None if row is None else self._to_model(row)

    def consume(self, uuid: UUID, consumed_at: int) -> bool:
        cursor = self.connection.execute(
            "UPDATE access_invitation SET consumed_at = ? WHERE uuid = ? AND consumed_at IS NULL AND revoked_at IS NULL AND created_at <= ? AND expires_at > ?",
            (consumed_at, uuid.bytes, consumed_at, consumed_at),
        )
        return cursor.rowcount == 1

    def revoke(self, uuid: UUID, revoked_at: int) -> None:
        self.connection.execute(
            "UPDATE access_invitation SET revoked_at = ? WHERE uuid = ? AND consumed_at IS NULL AND revoked_at IS NULL",
            (revoked_at, uuid.bytes),
        )

    def list_by_ledger(self, ledger_uuid: UUID) -> list[AccessInvitation]:
        rows = self.connection.execute(
            "SELECT uuid, ledger_uuid, grant_uuid, secret_hash, created_at, expires_at, consumed_at, revoked_at FROM access_invitation WHERE ledger_uuid = ?",
            (ledger_uuid.bytes,),
        ).fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: sqlite3.Row) -> AccessInvitation:
        return AccessInvitation.model_validate(dict(row))
