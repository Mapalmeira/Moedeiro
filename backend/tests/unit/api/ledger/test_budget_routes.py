import base64
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import UUID

from fastapi import HTTPException

from app.api.ledger.routes.budget import _parse_cursor, delete_ledger_budget, update_ledger_budget
from app.application.ledger.exceptions import BudgetNameUnavailableError, BudgetNotFoundError, CategoryNotFoundError


class BudgetRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.uuid = UUID("00000000-0000-0000-0000-000000000001")
        self.request = SimpleNamespace()
        self.factory = patch("app.api.ledger.routes.budget.ledger_unit_of_work_factory", return_value=object())
        self.factory.start()
        self.addCleanup(self.factory.stop)
        self.payload = SimpleNamespace(
            category_uuid=self.uuid,
            from_timestamp=10,
            to_timestamp=20,
            name="Food",
            description=None,
            amount=100,
        )

    def test_update_translates_not_found_and_name_conflict_errors(self) -> None:
        cases = (
            (BudgetNotFoundError, 404, "Budget not found"),
            (CategoryNotFoundError, 404, "Category not found"),
            (BudgetNameUnavailableError, 409, "Budget name unavailable"),
        )
        for error, status_code, detail in cases:
            with self.subTest(error=error), patch("app.api.ledger.routes.budget.update_budget", side_effect=error):
                with self.assertRaises(HTTPException) as raised:
                    update_ledger_budget(self.uuid, self.uuid, self.payload, self.request, object())
            self.assertEqual(raised.exception.status_code, status_code)
            self.assertEqual(raised.exception.detail, detail)

    def test_deletion_translates_an_unknown_budget(self) -> None:
        with patch("app.api.ledger.routes.budget.delete_budget", side_effect=BudgetNotFoundError):
            with self.assertRaises(HTTPException) as raised:
                delete_ledger_budget(self.uuid, self.uuid, self.request, object())

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(raised.exception.detail, "Budget not found")

    def test_cursor_rejects_an_empty_budget_name(self) -> None:
        cursor = base64.urlsafe_b64encode(f"{self.uuid.hex}:".encode("utf-8")).decode("ascii").rstrip("=")
        with self.assertRaisesRegex(ValueError, "invalid budget cursor"):
            _parse_cursor(cursor)
