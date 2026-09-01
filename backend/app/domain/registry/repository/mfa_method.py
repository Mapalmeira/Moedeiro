from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.mfa_method import MfaMethod, MfaMethodType


class MfaMethodRepository(ABC):
    @abstractmethod
    def create(self, user_uuid: UUID, type: MfaMethodType, secret_encrypted: bytes, created_at: int) -> MfaMethod:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> MfaMethod | None:
        pass

    @abstractmethod
    def get_totp_by_user(self, user_uuid: UUID) -> MfaMethod | None:
        pass

    @abstractmethod
    def delete(self, uuid: UUID) -> None:
        pass

    @abstractmethod
    def list_by_user(self, user_uuid: UUID) -> list[MfaMethod]:
        pass
