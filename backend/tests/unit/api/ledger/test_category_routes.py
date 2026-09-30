from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import UUID

from fastapi import HTTPException

from app.api.ledger.routes.category import create_ledger_category, delete_ledger_category, get_ledger_category, get_ledger_category_tree, update_ledger_category
from app.application.ledger.exceptions import CategoryDepthExceededError, CategoryInUseError, CategoryNameUnavailableError, CategoryNotFoundError, CategoryTreeSizeExceededError, InvalidCategoryHierarchyError


class CategoryRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.uuid = UUID("00000000-0000-0000-0000-000000000001")
        self.payload = SimpleNamespace(name="Food", icon="lucide:Utensils", color_code="#ffffff", parent_uuid=None)
        self.factory = patch("app.api.ledger.routes.category.ledger_unit_of_work_factory", return_value=object())
        self.factory.start()
        self.addCleanup(self.factory.stop)

    def test_create_translates_category_conflicts(self) -> None:
        cases = (
            (CategoryNotFoundError, 404, "Category not found"),
            (CategoryTreeSizeExceededError, 409, "Category limit exceeded"),
            (CategoryNameUnavailableError, 409, "Category name unavailable"),
            (CategoryDepthExceededError, 409, "Category depth limit exceeded"),
            (InvalidCategoryHierarchyError, 409, "Invalid category hierarchy"),
        )
        for error, status_code, detail in cases:
            with self.subTest(error=error), patch("app.api.ledger.routes.category.create_category", side_effect=error):
                with self.assertRaises(HTTPException) as raised:
                    create_ledger_category(self.uuid, self.payload, SimpleNamespace(), object())
            self.assertEqual(raised.exception.status_code, status_code)
            self.assertEqual(raised.exception.detail, detail)

    def test_read_update_and_delete_translate_errors(self) -> None:
        cases = (
            ("get_category", get_ledger_category, CategoryNotFoundError, 404, "Category not found"),
            ("get_category_tree", get_ledger_category_tree, CategoryTreeSizeExceededError, 409, "Category limit exceeded"),
            ("update_category", update_ledger_category, CategoryNameUnavailableError, 409, "Category name unavailable"),
            ("delete_category", delete_ledger_category, CategoryInUseError, 409, "Category is in use"),
        )
        for dependency, route, error, status_code, detail in cases:
            with self.subTest(dependency=dependency), patch(f"app.api.ledger.routes.category.{dependency}", side_effect=error):
                with self.assertRaises(HTTPException) as raised:
                    if route is get_ledger_category_tree:
                        route(self.uuid, SimpleNamespace(), object())
                    elif route is update_ledger_category:
                        route(self.uuid, self.uuid, self.payload, SimpleNamespace(), object())
                    else:
                        route(self.uuid, self.uuid, SimpleNamespace(), object())
            self.assertEqual(raised.exception.status_code, status_code)
            self.assertEqual(raised.exception.detail, detail)
