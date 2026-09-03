from collections.abc import Callable
from uuid import UUID

from app.application.ledger.exceptions import CategoryInUseError, CategoryNotFoundError
from app.application.ledger.unit_of_work import LedgerUnitOfWork
from app.domain.appearance import Icon, RgbColorCode
from app.domain.ledger.model.category import Category, CategoryName
from app.domain.ledger.model.category_tree_node import CategoryTreeNode


def create_category(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    name: CategoryName,
    icon: Icon,
    color_code: RgbColorCode,
    parent_uuid: UUID | None,
    max_tree_size: int,
) -> Category:
    with unit_of_work_factory() as unit_of_work:
        if parent_uuid is not None and unit_of_work.category_repository.get(parent_uuid) is None:
            raise CategoryNotFoundError
        if unit_of_work.category_repository.count() >= max_tree_size:
            raise ValueError(f"category tree must not contain more than {max_tree_size} categories")
        category = unit_of_work.category_repository.create(name, icon, color_code, parent_uuid)
        unit_of_work.commit()
    return category


def get_category(unit_of_work_factory: Callable[[], LedgerUnitOfWork], category_uuid: UUID) -> Category:
    with unit_of_work_factory() as unit_of_work:
        category = unit_of_work.category_repository.get(category_uuid)
        if category is None:
            raise CategoryNotFoundError
        return category


def get_category_tree(unit_of_work_factory: Callable[[], LedgerUnitOfWork], max_tree_size: int) -> list[CategoryTreeNode]:
    with unit_of_work_factory() as unit_of_work:
        return unit_of_work.category_repository.get_tree(max_tree_size)


def update_category(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    category_uuid: UUID,
    name: CategoryName,
    icon: Icon,
    color_code: RgbColorCode,
    parent_uuid: UUID | None,
) -> Category:
    with unit_of_work_factory() as unit_of_work:
        category = unit_of_work.category_repository.get(category_uuid)
        if category is None:
            raise CategoryNotFoundError
        if parent_uuid is not None and unit_of_work.category_repository.get(parent_uuid) is None:
            raise CategoryNotFoundError
        updated_category = Category.model_validate({**category.model_dump(), "name": name, "icon": icon, "color_code": color_code, "parent_uuid": parent_uuid})
        unit_of_work.category_repository.update_name(category.uuid, updated_category.name)
        unit_of_work.category_repository.update_icon(category.uuid, updated_category.icon)
        unit_of_work.category_repository.update_color_code(category.uuid, updated_category.color_code)
        unit_of_work.category_repository.update_parent(category.uuid, updated_category.parent_uuid)
        unit_of_work.commit()
    return updated_category


def delete_category(unit_of_work_factory: Callable[[], LedgerUnitOfWork], category_uuid: UUID) -> None:
    with unit_of_work_factory() as unit_of_work:
        if unit_of_work.category_repository.get(category_uuid) is None:
            raise CategoryNotFoundError
        if unit_of_work.category_repository.is_in_use(category_uuid):
            raise CategoryInUseError
        unit_of_work.category_repository.delete(category_uuid)
        unit_of_work.commit()
