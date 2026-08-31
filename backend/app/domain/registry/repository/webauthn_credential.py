from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.webauthn_credential import WebAuthnCredential


class WebAuthnCredentialRepository(ABC):
    @abstractmethod
    def create(self, user_uuid: UUID, credential_id: bytes, public_key: bytes, sign_count: int, created_at: int, name: str) -> WebAuthnCredential:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> WebAuthnCredential | None:
        pass

    @abstractmethod
    def get_by_credential_id(self, credential_id: bytes) -> WebAuthnCredential | None:
        pass

    @abstractmethod
    def update_usage(self, uuid: UUID, sign_count: int, last_used_at: int) -> None:
        pass

    @abstractmethod
    def update_name(self, uuid: UUID, value: str) -> None:
        pass

    @abstractmethod
    def delete(self, uuid: UUID) -> None:
        pass

    @abstractmethod
    def list_by_user(self, user_uuid: UUID) -> list[WebAuthnCredential]:
        pass
