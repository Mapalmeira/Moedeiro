import sqlite3
from uuid import UUID

from app.domain.registry.model.access_grant import AccessGrant
from app.domain.registry.repository.access_grant import AccessGrantRepository


class SqliteAccessGrantRepository(AccessGrantRepository):
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create_webcrypto(self, uuid: UUID, ledger_uuid: UUID, label: str | None, public_key: bytes, created_at: int) -> AccessGrant:
        grant = AccessGrant(uuid=uuid, ledger_uuid=ledger_uuid, authentication_method="WEBCRYPTO", label=label, public_key=public_key, algorithm="ES256", created_at=created_at)
        self._insert(grant)
        return grant

    def create_webauthn(self, uuid: UUID, ledger_uuid: UUID, label: str | None, public_key: bytes, credential_id: bytes, signature_counter: int, created_at: int) -> AccessGrant:
        grant = AccessGrant(uuid=uuid, ledger_uuid=ledger_uuid, authentication_method="WEBAUTHN", label=label, public_key=public_key, algorithm="ES256", credential_id=credential_id, signature_counter=signature_counter, created_at=created_at)
        self._insert(grant)
        return grant

    def get(self, uuid: UUID) -> AccessGrant | None:
        row = self.connection.execute(
            "SELECT uuid, ledger_uuid, authentication_method, label, public_key, algorithm, credential_id, signature_counter, created_at, revoked_at FROM access_grant WHERE uuid = ?",
            (uuid.bytes,),
        ).fetchone()
        return None if row is None else self._to_model(row)

    def get_by_credential_id(self, credential_id: bytes) -> AccessGrant | None:
        row = self.connection.execute(
            "SELECT uuid, ledger_uuid, authentication_method, label, public_key, algorithm, credential_id, signature_counter, created_at, revoked_at FROM access_grant WHERE credential_id = ?",
            (credential_id,),
        ).fetchone()
        return None if row is None else self._to_model(row)

    def update_webauthn_state(self, uuid: UUID, signature_counter: int) -> None:
        self.connection.execute(
            "UPDATE access_grant SET signature_counter = ? WHERE uuid = ? AND authentication_method = 'WEBAUTHN' AND revoked_at IS NULL",
            (signature_counter, uuid.bytes),
        )

    def revoke(self, uuid: UUID, revoked_at: int) -> None:
        self.connection.execute(
            "UPDATE access_grant SET revoked_at = ? WHERE uuid = ? AND revoked_at IS NULL",
            (revoked_at, uuid.bytes),
        )

    def list_by_ledger(self, ledger_uuid: UUID) -> list[AccessGrant]:
        rows = self.connection.execute(
            "SELECT uuid, ledger_uuid, authentication_method, label, public_key, algorithm, credential_id, signature_counter, created_at, revoked_at FROM access_grant WHERE ledger_uuid = ?",
            (ledger_uuid.bytes,),
        ).fetchall()
        return [self._to_model(row) for row in rows]

    def _insert(self, grant: AccessGrant) -> None:
        self.connection.execute(
            "INSERT INTO access_grant(uuid, ledger_uuid, authentication_method, label, public_key, algorithm, credential_id, signature_counter, created_at, revoked_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (grant.uuid.bytes, grant.ledger_uuid.bytes, grant.authentication_method, grant.label, grant.public_key, grant.algorithm, grant.credential_id, grant.signature_counter, grant.created_at, grant.revoked_at),
        )

    @staticmethod
    def _to_model(row: sqlite3.Row) -> AccessGrant:
        return AccessGrant.model_validate(dict(row))
