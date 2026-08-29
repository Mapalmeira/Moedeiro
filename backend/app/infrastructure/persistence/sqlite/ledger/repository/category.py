import sqlite3
from uuid import UUID, uuid4

from app.domain.ledger.model.category import Category
from app.domain.ledger.repository.category import CategoryRepository


class SqliteCategoryRepository(CategoryRepository):
    _SORT_COLUMNS = {"name": "category_name"}

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, name: str, parent_uuid: UUID | None) -> Category:
        category = Category(uuid=uuid4(), name=name, parent_uuid=parent_uuid)
        self.connection.execute(
            "INSERT INTO category(uuid, category_name, parent_uuid) VALUES (?, ?, ?)",
            (str(category.uuid), category.name, self._serialize_uuid(category.parent_uuid)),
        )
        return category

    def get(self, uuid: UUID) -> Category | None:
        row = self.connection.execute(
            "SELECT uuid, category_name AS name, parent_uuid FROM category WHERE uuid = ?",
            (str(uuid),),
        ).fetchone()
        if row is None:
            return None
        return self._to_model(row)

    def update_name(self, uuid: UUID, value: str) -> None:
        category = Category(uuid=uuid, name=value, parent_uuid=None)
        self.connection.execute(
            "UPDATE category SET category_name = ? WHERE uuid = ?",
            (category.name, str(category.uuid)),
        )

    def update_parent(self, uuid: UUID, parent_uuid: UUID | None) -> None:
        category = Category(uuid=uuid, name="category", parent_uuid=parent_uuid)
        self.connection.execute(
            "UPDATE category SET parent_uuid = ? WHERE uuid = ?",
            (self._serialize_uuid(category.parent_uuid), str(category.uuid)),
        )

    def list_all(self) -> list[Category]:
        rows = self.connection.execute(
            "SELECT uuid, category_name AS name, parent_uuid FROM category"
        ).fetchall()
        return [self._to_model(row) for row in rows]

    def list_page(self, page_number: int, page_size: int, sort_key: str, ascending: bool) -> list[Category]:
        self._validate_page(page_number, page_size)
        sort_column = self._get_sort_column(sort_key)
        direction = "ASC" if ascending else "DESC"
        offset = (page_number - 1) * page_size
        rows = self.connection.execute(
            f"""
            SELECT uuid, category_name AS name, parent_uuid
            FROM category
            ORDER BY {sort_column} {direction}, uuid ASC
            LIMIT ? OFFSET ?
            """,
            (page_size, offset),
        ).fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: sqlite3.Row) -> Category:
        return Category.model_validate(dict(row))

    @staticmethod
    def _serialize_uuid(value: UUID | None) -> str | None:
        if value is None:
            return None
        return str(value)

    @classmethod
    def _get_sort_column(cls, sort_key: str) -> str:
        try:
            return cls._SORT_COLUMNS[sort_key]
        except KeyError as error:
            raise ValueError(f"Invalid category sort key: {sort_key}") from error

    @staticmethod
    def _validate_page(page_number: int, page_size: int) -> None:
        if page_number < 1:
            raise ValueError("page_number must be greater than or equal to 1")
        if page_size < 1:
            raise ValueError("page_size must be greater than or equal to 1")
