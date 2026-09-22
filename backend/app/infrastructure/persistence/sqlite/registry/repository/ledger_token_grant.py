import sqlite3
from uuid import UUID

from app.domain.registry.model.ledger_grant import LedgerGrant
from app.domain.registry.model.ledger_token_grant import LedgerTokenGrant
from app.domain.registry.repository.ledger_token_grant import LedgerTokenGrantRepository


class SqliteLedgerTokenGrantRepository(LedgerTokenGrantRepository):
    _select = """
        SELECT
            grant.uuid AS grant_uuid,
            grant.user_uuid AS grant_user_uuid,
            grant.ledger_uuid AS grant_ledger_uuid,
            grant.type AS grant_type,
            grant.created_at AS grant_created_at,
            grant.revoked_at AS grant_revoked_at,
            token.name AS token_name,
            token.token_hash AS token_hash
        FROM ledger_token_grant AS token
        JOIN ledger_grant AS grant
          ON grant.uuid = token.uuid
         AND grant.type = token.type
    """

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, grant: LedgerGrant, name: str, token_hash: bytes) -> LedgerTokenGrant:
        token_grant = LedgerTokenGrant(grant=grant, name=name, token_hash=token_hash)
        self.connection.execute(
            "INSERT INTO ledger_token_grant(uuid, type, name, token_hash) VALUES (?, ?, ?, ?)",
            (token_grant.grant.uuid.bytes, token_grant.grant.type, token_grant.name, token_grant.token_hash),
        )
        return token_grant

    def get(self, uuid: UUID) -> LedgerTokenGrant | None:
        row = self.connection.execute(f"{self._select} WHERE token.uuid = ?", (uuid.bytes,)).fetchone()
        return None if row is None else self._to_model(row)

    def get_by_token_hash(self, token_hash: bytes) -> LedgerTokenGrant | None:
        row = self.connection.execute(f"{self._select} WHERE token.token_hash = ?", (token_hash,)).fetchone()
        return None if row is None else self._to_model(row)

    @staticmethod
    def _to_model(row: sqlite3.Row) -> LedgerTokenGrant:
        grant = LedgerGrant(
            uuid=row["grant_uuid"],
            user_uuid=row["grant_user_uuid"],
            ledger_uuid=row["grant_ledger_uuid"],
            type=row["grant_type"],
            created_at=row["grant_created_at"],
            revoked_at=row["grant_revoked_at"],
        )
        return LedgerTokenGrant(grant=grant, name=row["token_name"], token_hash=row["token_hash"])
