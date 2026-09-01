import sqlite3
from uuid import UUID, uuid4

from pydantic import TypeAdapter

from app.domain.appearance import Icon, RgbColorCode
from app.domain.ledger.model.category import Category, CategoryName
from app.domain.ledger.model.category_tree_node import CategoryTreeNode
from app.domain.ledger.repository.category import CategoryRepository


class SqliteCategoryRepository(CategoryRepository):
    _SORT_COLUMNS = {"name": "category_name"}
    _name_adapter = TypeAdapter(CategoryName)
    _icon_adapter = TypeAdapter(Icon)
    _color_code_adapter = TypeAdapter(RgbColorCode)

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, name: CategoryName, icon: Icon, color_code: RgbColorCode, parent_uuid: UUID | None) -> Category:
        category = Category(uuid=uuid4(), name=name, icon=icon, color_code=color_code, parent_uuid=parent_uuid)
        self.connection.execute(
            "INSERT INTO category(uuid, category_name, icon, color_code, parent_uuid) VALUES (?, ?, ?, ?, ?)",
            (category.uuid.bytes, category.name, category.icon, category.color_code, self._serialize_uuid(category.parent_uuid)),
        )
        return category

    def get(self, uuid: UUID) -> Category | None:
        row = self.connection.execute(
            "SELECT uuid, category_name AS name, icon, color_code, parent_uuid FROM category WHERE uuid = ?",
            (uuid.bytes,),
        ).fetchone()
        if row is None:
            return None
        return self._to_model(row)

    def update_name(self, uuid: UUID, value: CategoryName) -> None:
        name = self._name_adapter.validate_python(value)
        self.connection.execute(
            "UPDATE category SET category_name = ? WHERE uuid = ?",
            (name, uuid.bytes),
        )

    def update_icon(self, uuid: UUID, value: Icon) -> None:
        icon = self._icon_adapter.validate_python(value)
        self.connection.execute(
            "UPDATE category SET icon = ? WHERE uuid = ?",
            (icon, uuid.bytes),
        )

    def update_color_code(self, uuid: UUID, value: RgbColorCode) -> None:
        color_code = self._color_code_adapter.validate_python(value)
        self.connection.execute(
            "UPDATE category SET color_code = ? WHERE uuid = ?",
            (color_code, uuid.bytes),
        )

    def update_parent(self, uuid: UUID, parent_uuid: UUID | None) -> None:
        self.connection.execute(
            "UPDATE category SET parent_uuid = ? WHERE uuid = ?",
            (self._serialize_uuid(parent_uuid), uuid.bytes),
        )

    def list_all(self) -> list[Category]:
        rows = self.connection.execute(
            "SELECT uuid, category_name AS name, icon, color_code, parent_uuid FROM category"
        ).fetchall()
        return [self._to_model(row) for row in rows]

    def get_tree(self) -> list[CategoryTreeNode]:
        rows = self.connection.execute(
            """
            SELECT uuid, category_name AS name, icon, color_code, parent_uuid
            FROM category
            ORDER BY category_name ASC, uuid ASC
            """
        ).fetchall()
        categories = [self._to_model(row) for row in rows]
        nodes = {category.uuid: CategoryTreeNode(category=category) for category in categories}
        roots: list[CategoryTreeNode] = []

        for category in categories:
            node = nodes[category.uuid]
            if category.parent_uuid is None:
                roots.append(node)
                continue
            nodes[category.parent_uuid].children.append(node)

        return roots

    def list_page(self, page_number: int, page_size: int, sort_key: str, ascending: bool) -> list[Category]:
        self._validate_page(page_number, page_size)
        sort_column = self._get_sort_column(sort_key)
        direction = "ASC" if ascending else "DESC"
        offset = (page_number - 1) * page_size
        rows = self.connection.execute(
            f"""
            SELECT uuid, category_name AS name, icon, color_code, parent_uuid
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
    def _serialize_uuid(value: UUID | None) -> bytes | None:
        if value is None:
            return None
        return value.bytes

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
