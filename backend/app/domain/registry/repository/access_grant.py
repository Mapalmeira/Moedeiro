from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.access_grant import AccessGrant


class AccessGrantRepository(ABC):
    @abstractmethod
    def create_webcrypto(self, uuid: UUID, ledger_uuid: UUID, label: str | None, public_key: bytes, created_at: int) -> AccessGrant:
        pass

    @abstractmethod
    def create_webauthn(self, uuid: UUID, ledger_uuid: UUID, label: str | None, public_key: bytes, credential_id: bytes, signature_counter: int, created_at: int) -> AccessGrant:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> AccessGrant | None:
        pass

    @abstractmethod
    def get_by_credential_id(self, credential_id: bytes) -> AccessGrant | None:
        pass

    @abstractmethod
    def update_webauthn_state(self, uuid: UUID, signature_counter: int) -> None:
        pass

    @abstractmethod
    def revoke(self, uuid: UUID, revoked_at: int) -> None:
        pass

    @abstractmethod
    def list_by_ledger(self, ledger_uuid: UUID) -> list[AccessGrant]:
        pass
