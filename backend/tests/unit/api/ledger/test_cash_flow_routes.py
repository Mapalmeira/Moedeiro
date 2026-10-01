from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import UUID

from fastapi import HTTPException

from app.api.ledger.routes.cash_flow import get_ledger_cash_flow, get_ledger_cash_flow_sankey, list_ledger_cash_flow_points
from app.application.ledger.exceptions import AccountNotFoundError, CategoryNotFoundError, CurrencyNotFoundError, InvalidQueryParameterError, QueryPointLimitExceededError


class CashFlowRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.uuid = UUID("00000000-0000-0000-0000-000000000001")
        self.request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace(max_query_points=50))))
        self.factory = patch("app.api.ledger.routes.cash_flow.ledger_unit_of_work_factory", return_value=object())
        self.factory.start()
        self.addCleanup(self.factory.stop)

    def test_summary_translates_unknown_filter_resources(self) -> None:
        cases = (
            (CurrencyNotFoundError, "Currency not found"),
            (AccountNotFoundError, "Account not found"),
            (CategoryNotFoundError, "Category not found"),
        )
        for error, detail in cases:
            with self.subTest(error=error), patch("app.api.ledger.routes.cash_flow.get_cash_flow_summary", side_effect=error):
                with self.assertRaises(HTTPException) as raised:
                    get_ledger_cash_flow(self.uuid, self.uuid, 10, 20, self.request, object())
            self.assertEqual(raised.exception.status_code, 404)
            self.assertEqual(raised.exception.detail, detail)

    def test_points_translate_query_errors(self) -> None:
        cases = (
            (CurrencyNotFoundError, 404, "Currency not found"),
            (AccountNotFoundError, 404, "Account not found"),
            (CategoryNotFoundError, 404, "Category not found"),
            (QueryPointLimitExceededError, 422, "Point count cannot exceed 50"),
            (InvalidQueryParameterError, 422, "Invalid query parameters"),
        )
        for error, status_code, detail in cases:
            with self.subTest(error=error), patch("app.api.ledger.routes.cash_flow.list_cash_flow_points", side_effect=error):
                with self.assertRaises(HTTPException) as raised:
                    list_ledger_cash_flow_points(self.uuid, self.uuid, 10, 20, 1, self.request, object())
            self.assertEqual(raised.exception.status_code, status_code)
            self.assertEqual(raised.exception.detail, detail)

    def test_sankey_translates_unknown_scope_relations_and_invalid_dimensions(self) -> None:
        cases = (
            (CurrencyNotFoundError, 404, "Currency not found"),
            (AccountNotFoundError, 404, "Account not found"),
            (InvalidQueryParameterError, 422, "Invalid query parameters"),
        )
        for error, status_code, detail in cases:
            with self.subTest(error=error), patch("app.api.ledger.routes.cash_flow.get_cash_flow_sankey", side_effect=error):
                with self.assertRaises(HTTPException) as raised:
                    get_ledger_cash_flow_sankey(self.uuid, self.uuid, 10, 20, 1, self.request, object(), self.uuid)
            self.assertEqual(raised.exception.status_code, status_code)
            self.assertEqual(raised.exception.detail, detail)

    def test_points_and_sankey_reject_an_empty_period(self) -> None:
        for route, arguments in (
            (list_ledger_cash_flow_points, (self.uuid, self.uuid, 20, 20, 1, self.request, object())),
            (get_ledger_cash_flow_sankey, (self.uuid, self.uuid, 20, 20, 1, self.request, object(), self.uuid)),
        ):
            with self.subTest(route=route.__name__), self.assertRaises(HTTPException) as raised:
                route(*arguments)
            self.assertEqual(raised.exception.detail, "from_timestamp must be less than to_timestamp")
