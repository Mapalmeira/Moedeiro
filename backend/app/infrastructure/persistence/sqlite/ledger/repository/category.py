import sqlite3
from collections.abc import Collection
from uuid import UUID, uuid4

from pydantic import TypeAdapter

from app.application.ledger.exceptions import CategoryTreeSizeExceededError, InvalidCategoryHierarchyError
from app.domain.appearance import Icon, RgbColorCode
from app.domain.ledger.model.category import Category, CategoryName, MAX_CATEGORY_DEPTH
from app.domain.ledger.model.category_tree_node import CategoryTreeNode
from app.domain.ledger.repository.category import CategoryRepository


class SqliteCategoryRepository(CategoryRepository):
    _name_adapter = TypeAdapter(CategoryName)
    _icon_adapter = TypeAdapter(Icon)
    _color_code_adapter = TypeAdapter(RgbColorCode)

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, name: CategoryName, icon: Icon, color_code: RgbColorCode, parent_uuid: UUID | None) -> Category:
        category = Category(uuid=uuid4(), name=name, icon=icon, color_code=color_code, parent_uuid=parent_uuid)
        if parent_uuid is not None:
            ancestors = self._get_ancestors(parent_uuid)
            if ancestors is not None and len(ancestors) >= MAX_CATEGORY_DEPTH:
                raise InvalidCategoryHierarchyError
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

    def get_by_name(self, name: CategoryName) -> Category | None:
        category_name = self._name_adapter.validate_python(name)
        row = self.connection.execute(
            "SELECT uuid, category_name AS name, icon, color_code, parent_uuid FROM category WHERE category_name = ?",
            (category_name,),
        ).fetchone()
        if row is None:
            return None
        return self._to_model(row)

    def get_many(self, uuids: Collection[UUID]) -> list[Category]:
        unique_uuids = set(uuids)
        if not unique_uuids:
            return []
        placeholders = ", ".join("?" for _ in unique_uuids)
        rows = self.connection.execute(
            f"SELECT uuid, category_name AS name, icon, color_code, parent_uuid FROM category WHERE uuid IN ({placeholders})",
            tuple(uuid.bytes for uuid in unique_uuids),
        ).fetchall()
        return [self._to_model(row) for row in rows]

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
        if parent_uuid is not None and self.get(uuid) is not None:
            ancestors = self._get_ancestors(parent_uuid)
            if ancestors is not None:
                if uuid in ancestors:
                    raise InvalidCategoryHierarchyError
                if len(ancestors) + self._get_subtree_height(uuid) > MAX_CATEGORY_DEPTH:
                    raise InvalidCategoryHierarchyError
        self.connection.execute(
            "UPDATE category SET parent_uuid = ? WHERE uuid = ?",
            (self._serialize_uuid(parent_uuid), uuid.bytes),
        )

    def count(self) -> int:
        return self.connection.execute("SELECT COUNT(*) FROM category").fetchone()[0]

    def get_tree(self, max_size: int) -> list[CategoryTreeNode]:
        rows = self.connection.execute(
            """
            SELECT uuid, category_name AS name, icon, color_code, parent_uuid
            FROM category
            ORDER BY category_name ASC, uuid ASC
            LIMIT ?
            """,
            (max_size + 1,),
        ).fetchall()
        if len(rows) > max_size:
            raise CategoryTreeSizeExceededError
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

    def is_in_use(self, uuid: UUID) -> bool:
        row = self.connection.execute(
            """
            WITH RECURSIVE category_subtree(uuid) AS (
                SELECT uuid FROM category WHERE uuid = ?

                UNION ALL

                SELECT child.uuid
                FROM category AS child
                JOIN category_subtree AS parent ON child.parent_uuid = parent.uuid
            )
            SELECT EXISTS(
                SELECT 1
                FROM financial_movement
                WHERE category_uuid IN (SELECT uuid FROM category_subtree)
            ) OR EXISTS(
                SELECT 1
                FROM budget
                WHERE category_uuid IN (SELECT uuid FROM category_subtree)
            )
            """,
            (uuid.bytes,),
        ).fetchone()
        return bool(row[0])

    def delete(self, uuid: UUID) -> None:
        self.connection.execute("DELETE FROM category WHERE uuid = ?", (uuid.bytes,))

    @staticmethod
    def _to_model(row: sqlite3.Row) -> Category:
        return Category.model_validate(dict(row))

    @staticmethod
    def _serialize_uuid(value: UUID | None) -> bytes | None:
        if value is None:
            return None
        return value.bytes

    def _get_ancestors(self, uuid: UUID) -> list[UUID] | None:
        ancestors: list[UUID] = []
        current_uuid = uuid
        while True:
            if current_uuid in ancestors:
                raise InvalidCategoryHierarchyError
            row = self.connection.execute("SELECT parent_uuid FROM category WHERE uuid = ?", (current_uuid.bytes,)).fetchone()
            if row is None:
                return None
            ancestors.append(current_uuid)
            if row["parent_uuid"] is None:
                return ancestors
            current_uuid = UUID(bytes=row["parent_uuid"])

    def _get_subtree_height(self, uuid: UUID) -> int:
        row = self.connection.execute(
            """
            WITH RECURSIVE descendants(uuid, depth) AS (
                SELECT uuid, 1
                FROM category
                WHERE uuid = ?

                UNION ALL

                SELECT child.uuid, parent.depth + 1
                FROM category AS child
                JOIN descendants AS parent ON child.parent_uuid = parent.uuid
                WHERE parent.depth < ?
            )
            SELECT MAX(depth) AS height
            FROM descendants
            """,
            (uuid.bytes, MAX_CATEGORY_DEPTH + 1),
        ).fetchone()
        assert row is not None
        return row["height"]
