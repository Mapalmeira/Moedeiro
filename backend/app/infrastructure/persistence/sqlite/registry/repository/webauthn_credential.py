import sqlite3
from uuid import UUID, uuid4

from pydantic import TypeAdapter

from app.domain.registry.model.webauthn_credential import WebAuthnCredential, WebAuthnCredentialName
from app.domain.registry.repository.webauthn_credential import WebAuthnCredentialRepository


class SqliteWebAuthnCredentialRepository(WebAuthnCredentialRepository):
    _columns = "uuid, user_uuid, credential_id, public_key, sign_count, created_at, last_used_at, name"
    _name_adapter = TypeAdapter(WebAuthnCredentialName)

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, user_uuid: UUID, credential_id: bytes, public_key: bytes, sign_count: int, created_at: int, name: str) -> WebAuthnCredential:
        credential = WebAuthnCredential(uuid=uuid4(), user_uuid=user_uuid, credential_id=credential_id, public_key=public_key, sign_count=sign_count, created_at=created_at, name=name)
        self.connection.execute(
            "INSERT INTO webauthn_credential(uuid, user_uuid, credential_id, public_key, sign_count, created_at, last_used_at, name) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (credential.uuid.bytes, credential.user_uuid.bytes, credential.credential_id, credential.public_key, credential.sign_count, credential.created_at, credential.last_used_at, credential.name),
        )
        return credential

    def get(self, uuid: UUID) -> WebAuthnCredential | None:
        row = self.connection.execute(f"SELECT {self._columns} FROM webauthn_credential WHERE uuid = ?", (uuid.bytes,)).fetchone()
        return None if row is None else self._to_model(row)

    def get_by_credential_id(self, credential_id: bytes) -> WebAuthnCredential | None:
        row = self.connection.execute(f"SELECT {self._columns} FROM webauthn_credential WHERE credential_id = ?", (credential_id,)).fetchone()
        return None if row is None else self._to_model(row)

    def update_usage(self, uuid: UUID, sign_count: int, last_used_at: int) -> None:
        credential = self.get(uuid)
        if credential is None:
            return
        WebAuthnCredential.model_validate({**credential.model_dump(), "sign_count": sign_count, "last_used_at": last_used_at})
        self.connection.execute("UPDATE webauthn_credential SET sign_count = ?, last_used_at = ? WHERE uuid = ?", (sign_count, last_used_at, uuid.bytes))

    def update_name(self, uuid: UUID, value: str) -> None:
        name = self._name_adapter.validate_python(value)
        self.connection.execute("UPDATE webauthn_credential SET name = ? WHERE uuid = ?", (name, uuid.bytes))

    def delete(self, uuid: UUID) -> None:
        self.connection.execute("DELETE FROM webauthn_credential WHERE uuid = ?", (uuid.bytes,))

    def list_by_user(self, user_uuid: UUID) -> list[WebAuthnCredential]:
        rows = self.connection.execute(f"SELECT {self._columns} FROM webauthn_credential WHERE user_uuid = ?", (user_uuid.bytes,)).fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: sqlite3.Row) -> WebAuthnCredential:
        return WebAuthnCredential.model_validate(dict(row))
