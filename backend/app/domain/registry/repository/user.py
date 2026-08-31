from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.user import User


class UserRepository(ABC):
    @abstractmethod
    def create(self, name: str, password_hash: str, created_at: int) -> User:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> User | None:
        pass

    @abstractmethod
    def get_by_normalized_name(self, normalized_name: str) -> User | None:
        pass

    @abstractmethod
    def update_name(self, uuid: UUID, value: str) -> None:
        pass

    @abstractmethod
    def update_password(self, uuid: UUID, expected_password_hash: str, new_password_hash: str, changed_at: int) -> bool:
        pass

    @abstractmethod
    def list_all(self) -> list[User]:
        pass
