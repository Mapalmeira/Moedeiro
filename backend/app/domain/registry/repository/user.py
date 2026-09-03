from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.registry.model.user import NormalizedUserName, User, UserName


class UserRepository(ABC):
    @abstractmethod
    def create(self, name: UserName, password_hash: str, created_at: int) -> User:
        pass

    @abstractmethod
    def get(self, uuid: UUID) -> User | None:
        pass

    @abstractmethod
    def get_by_normalized_name(self, normalized_name: NormalizedUserName) -> User | None:
        pass

    @abstractmethod
    def update_name(self, uuid: UUID, value: UserName) -> None:
        pass

    @abstractmethod
    def update_password(self, uuid: UUID, expected_password_hash: str, new_password_hash: str, changed_at: int) -> bool:
        pass

    @abstractmethod
    def delete(self, uuid: UUID) -> None:
        pass

    @abstractmethod
    def list_all(self, sort_key: str, ascending: bool) -> list[User]:
        pass
