import sqlite3
from uuid import UUID, uuid4

from pydantic import TypeAdapter

from app.domain.registry.model.user import NormalizedUserName, User, UserName, normalize_user_name
from app.domain.registry.repository.user import UserRepository


class SqliteUserRepository(UserRepository):
    _columns = "uuid, name, normalized_name, password_hash, created_at, password_changed_at"
    _SORT_COLUMNS = {
        "name": "user_account.name",
        "created_at": "user_account.created_at",
    }
    _name_adapter = TypeAdapter(UserName)
    _normalized_name_adapter = TypeAdapter(NormalizedUserName)

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, name: UserName, password_hash: str, created_at: int) -> User:
        user = User(uuid=uuid4(), name=name, normalized_name=normalize_user_name(name), password_hash=password_hash, created_at=created_at, password_changed_at=created_at)
        self.connection.execute(
            "INSERT INTO user_account(uuid, name, normalized_name, password_hash, created_at, password_changed_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user.uuid.bytes, user.name, user.normalized_name, user.password_hash, user.created_at, user.password_changed_at),
        )
        return user

    def get(self, uuid: UUID) -> User | None:
        row = self.connection.execute(f"SELECT {self._columns} FROM user_account WHERE uuid = ?", (uuid.bytes,)).fetchone()
        return None if row is None else self._to_model(row)

    def get_by_normalized_name(self, normalized_name: NormalizedUserName) -> User | None:
        value = self._normalized_name_adapter.validate_python(normalized_name)
        row = self.connection.execute(f"SELECT {self._columns} FROM user_account WHERE normalized_name = ?", (value,)).fetchone()
        return None if row is None else self._to_model(row)

    def update_name(self, uuid: UUID, value: UserName) -> None:
        name = self._name_adapter.validate_python(value)
        normalized_name = self._normalized_name_adapter.validate_python(normalize_user_name(name))
        self.connection.execute("UPDATE user_account SET name = ?, normalized_name = ? WHERE uuid = ?", (name, normalized_name, uuid.bytes))

    def update_password(self, uuid: UUID, expected_password_hash: str, new_password_hash: str, changed_at: int) -> bool:
        user = self.get(uuid)
        if user is None:
            return False
        User.model_validate({**user.model_dump(), "password_hash": new_password_hash, "password_changed_at": changed_at})
        cursor = self.connection.execute(
            "UPDATE user_account SET password_hash = ?, password_changed_at = ? WHERE uuid = ? AND password_hash = ?",
            (new_password_hash, changed_at, uuid.bytes, expected_password_hash),
        )
        return cursor.rowcount == 1

    def delete(self, uuid: UUID) -> None:
        self.connection.execute("DELETE FROM user_account WHERE uuid = ?", (uuid.bytes,))

    def list_all(self, sort_key: str, ascending: bool) -> list[User]:
        sort_column = self._get_sort_column(sort_key)
        direction = "ASC" if ascending else "DESC"
        rows = self.connection.execute(f"SELECT {self._columns} FROM user_account ORDER BY {sort_column} {direction}, user_account.uuid ASC").fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: sqlite3.Row) -> User:
        return User.model_validate(dict(row))

    @classmethod
    def _get_sort_column(cls, sort_key: str) -> str:
        try:
            return cls._SORT_COLUMNS[sort_key]
        except KeyError as error:
            raise ValueError(f"Invalid user sort key: {sort_key}") from error
