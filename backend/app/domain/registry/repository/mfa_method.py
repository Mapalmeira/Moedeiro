from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.mfa_method import MfaMethod, MfaMethodType


class MfaMethodRepository(ABC):
    @abstractmethod
    def create(self, user_uuid: UUID, type: MfaMethodType, secret_encrypted: bytes, created_at: int, confirmed_at: int | None = None, last_used_counter: int | None = None) -> MfaMethod:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> MfaMethod | None:
        pass

    @abstractmethod
    def get_totp_by_user(self, user_uuid: UUID) -> MfaMethod | None:
        pass

    @abstractmethod
    def is_totp_enabled(self, user_uuid: UUID) -> bool:
        pass

    @abstractmethod
    def confirm(self, uuid: UUID, confirmed_at: int, last_used_counter: int) -> bool:
        pass

    @abstractmethod
    def use_totp_counter(self, uuid: UUID, counter: int) -> bool:
        pass

    @abstractmethod
    def delete_unconfirmed_before(self, timestamp: int) -> int:
        pass

    @abstractmethod
    def delete(self, uuid: UUID) -> None:
        pass

    @abstractmethod
    def list_by_user(self, user_uuid: UUID) -> list[MfaMethod]:
        pass
