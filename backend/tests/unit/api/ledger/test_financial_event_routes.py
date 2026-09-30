from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import UUID

from fastapi import HTTPException

from app.api.ledger.routes.financial_event import create_ledger_financial_event, delete_ledger_financial_event, get_ledger_financial_event, list_ledger_financial_events, update_ledger_financial_event
from app.api.ledger.schema.financial_event import SimpleFinancialEventRequest
from app.application.ledger.exceptions import AccountNotFoundError, CategoryNotFoundError, CurrencyNotFoundError, FinancialEventLimitReachedError, FinancialEventNotFoundError, FinancialEventTypeMismatchError, FinancialMovementNotFoundError, InvalidFinancialEventError, InvalidFinancialEventStructureError


class FinancialEventRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.uuid = UUID("00000000-0000-0000-0000-000000000001")
        self.request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace(max_page_size=50))))
        self.payload = SimpleFinancialEventRequest(
            type="TRANSACTION",
            occurred_at=10,
            description="Lunch",
            account_uuid=self.uuid,
            category_uuid=self.uuid,
            value=-100,
        )
        self.factory = patch("app.api.ledger.routes.financial_event.ledger_unit_of_work_factory", return_value=object())
        self.factory.start()
        self.addCleanup(self.factory.stop)

    def test_create_translates_domain_errors(self) -> None:
        cases = (
            (AccountNotFoundError, 404, "Account not found"),
            (CategoryNotFoundError, 404, "Category not found"),
            (FinancialEventLimitReachedError, 409, "Financial event limit reached"),
            (InvalidFinancialEventError, 422, "Invalid financial event"),
        )
        for error, status_code, detail in cases:
            with self.subTest(error=error), patch("app.api.ledger.routes.financial_event.create_simple_financial_event", side_effect=error):
                with self.assertRaises(HTTPException) as raised:
                    create_ledger_financial_event(self.uuid, self.payload, self.request, object())
            self.assertEqual(raised.exception.status_code, status_code)
            self.assertEqual(raised.exception.detail, detail)

    def test_list_rejects_invalid_range_cursor_and_currency(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            list_ledger_financial_events(self.uuid, self.request, object(), 10, 10, 10)
        self.assertEqual(raised.exception.detail, "from_timestamp must be less than to_timestamp")

        with self.assertRaises(HTTPException) as raised:
            list_ledger_financial_events(self.uuid, self.request, object(), 10, 20, 10, cursor="invalid")
        self.assertEqual(raised.exception.detail, "Invalid cursor")

        with patch("app.api.ledger.routes.financial_event.list_financial_events_after", side_effect=CurrencyNotFoundError):
            with self.assertRaises(HTTPException) as raised:
                list_ledger_financial_events(self.uuid, self.request, object(), 10, 20, 10)
        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(raised.exception.detail, "Currency not found")

    def test_get_and_delete_translate_unknown_event(self) -> None:
        for dependency, route in (("get_financial_event", get_ledger_financial_event), ("delete_financial_event", delete_ledger_financial_event)):
            with self.subTest(dependency=dependency), patch(f"app.api.ledger.routes.financial_event.{dependency}", side_effect=FinancialEventNotFoundError):
                with self.assertRaises(HTTPException) as raised:
                    route(self.uuid, self.uuid, self.request, object())
            self.assertEqual(raised.exception.status_code, 404)
            self.assertEqual(raised.exception.detail, "Financial event not found")

    def test_update_translates_domain_errors(self) -> None:
        cases = (
            (FinancialEventNotFoundError, 404, "Financial event not found"),
            (FinancialMovementNotFoundError, 404, "Financial movement not found"),
            (AccountNotFoundError, 404, "Account not found"),
            (CategoryNotFoundError, 404, "Category not found"),
            (FinancialEventTypeMismatchError, 409, "Financial event type cannot be changed"),
            (InvalidFinancialEventStructureError, 409, "Stored financial event structure is invalid"),
            (InvalidFinancialEventError, 422, "Invalid financial event"),
        )
        for error, status_code, detail in cases:
            with self.subTest(error=error), patch("app.api.ledger.routes.financial_event.update_simple_financial_event", side_effect=error):
                with self.assertRaises(HTTPException) as raised:
                    update_ledger_financial_event(self.uuid, self.uuid, self.payload, self.request, object())
            self.assertEqual(raised.exception.status_code, status_code)
            self.assertEqual(raised.exception.detail, detail)
