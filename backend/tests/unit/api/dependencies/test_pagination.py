from types import SimpleNamespace
import unittest
from fastapi import HTTPException

from app.api.dependencies.pagination import validate_requested_page, validate_page_size


class PaginationDependenciesTest(unittest.TestCase):
    def test_requested_page_rejects_page_numbers_before_one(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            validate_requested_page(SimpleNamespace(), page_number=0, page_size=1)

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(raised.exception.detail, "page_number must be greater than or equal to 1")

    def test_page_size_rejects_values_before_one_and_above_the_configured_limit(self) -> None:
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace(max_page_size=20))))

        for page_size, detail in (
            (0, "page_size must be greater than or equal to 1"),
            (21, "page_size must be less than or equal to 20"),
        ):
            with self.subTest(page_size=page_size), self.assertRaises(HTTPException) as raised:
                validate_page_size(request, page_size)

            self.assertEqual(raised.exception.status_code, 422)
            self.assertEqual(raised.exception.detail, detail)

        with self.assertRaises(HTTPException) as raised:
            validate_requested_page(request, page_number=1, page_size=0)

        self.assertEqual(raised.exception.detail, "page_size must be greater than or equal to 1")
