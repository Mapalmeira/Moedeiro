import sqlite3
from uuid import UUID, uuid4

from app.domain.ledger.model.tag import Tag
from app.domain.ledger.repository.tag import TagRepository


class SqliteTagRepository(TagRepository):
    _SORT_COLUMNS = {"name": "name"}

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, name: str) -> None:
        tag = Tag(uuid=uuid4(), name=name)
        self.connection.execute(
            "INSERT INTO tag(uuid, name) VALUES (?, ?)",
            (str(tag.uuid), tag.name),
        )

    def get(self, uuid: UUID) -> Tag | None:
        row = self.connection.execute(
            "SELECT uuid, name FROM tag WHERE uuid = ?",
            (str(uuid),),
        ).fetchone()
        if row is None:
            return None
        return self._to_model(row)

    def update_name(self, uuid: UUID, value: str) -> None:
        tag = Tag(uuid=uuid, name=value)
        self.connection.execute(
            "UPDATE tag SET name = ? WHERE uuid = ?",
            (tag.name, str(tag.uuid)),
        )

    def list_all(self) -> list[Tag]:
        rows = self.connection.execute("SELECT uuid, name FROM tag").fetchall()
        return [self._to_model(row) for row in rows]

    def list_page(self, page_number: int, page_size: int, sort_key: str, ascending: bool) -> list[Tag]:
        self._validate_page(page_number, page_size)
        sort_column = self._get_sort_column(sort_key)
        direction = "ASC" if ascending else "DESC"
        offset = (page_number - 1) * page_size
        rows = self.connection.execute(
            f"""
            SELECT uuid, name
            FROM tag
            ORDER BY {sort_column} {direction}, uuid ASC
            LIMIT ? OFFSET ?
            """,
            (page_size, offset),
        ).fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: sqlite3.Row) -> Tag:
        return Tag.model_validate(dict(row))

    @classmethod
    def _get_sort_column(cls, sort_key: str) -> str:
        try:
            return cls._SORT_COLUMNS[sort_key]
        except KeyError as error:
            raise ValueError(f"Invalid tag sort key: {sort_key}") from error

    @staticmethod
    def _validate_page(page_number: int, page_size: int) -> None:
        if page_number < 1:
            raise ValueError("page_number must be greater than or equal to 1")
        if page_size < 1:
            raise ValueError("page_size must be greater than or equal to 1")
