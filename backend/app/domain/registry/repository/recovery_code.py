from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.recovery_code import RecoveryCode


class RecoveryCodeRepository(ABC):
    @abstractmethod
    def create(self, user_uuid: UUID, code_hash: bytes, created_at: int, expires_at: int) -> RecoveryCode:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> RecoveryCode | None:
        pass

    @abstractmethod
    def get_active_by_user(self, user_uuid: UUID, timestamp: int) -> RecoveryCode | None:
        pass

    @abstractmethod
    def consume(self, uuid: UUID, used_at: int) -> bool:
        pass

    @abstractmethod
    def delete_active_by_user(self, user_uuid: UUID) -> int:
        pass

    @abstractmethod
    def delete_inactive_before(self, timestamp: int) -> int:
        pass

    @abstractmethod
    def list_by_user(self, user_uuid: UUID) -> list[RecoveryCode]:
        pass
