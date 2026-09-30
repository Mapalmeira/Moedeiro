from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import UUID

from fastapi import HTTPException

from app.api.ledger.routes.currency import create_ledger_currency, delete_ledger_currency, get_ledger_currency, update_ledger_currency
from app.application.ledger.exceptions import CurrencyInUseError, CurrencyLimitReachedError, CurrencyNameUnavailableError, CurrencyNotFoundError


class CurrencyRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.uuid = UUID("00000000-0000-0000-0000-000000000001")
        self.payload = SimpleNamespace(name="Real", prefix="R$", suffix=None, decimal_places=2, icon="lucide:Banknote", color_code="#ffffff")
        self.factory = patch("app.api.ledger.routes.currency.ledger_unit_of_work_factory", return_value=object())
        self.factory.start()
        self.addCleanup(self.factory.stop)

    def test_create_translates_limit_and_name_conflict(self) -> None:
        cases = ((CurrencyLimitReachedError, "Currency limit reached"), (CurrencyNameUnavailableError, "Currency name unavailable"))
        for error, detail in cases:
            with self.subTest(error=error), patch("app.api.ledger.routes.currency.create_currency", side_effect=error):
                with self.assertRaises(HTTPException) as raised:
                    create_ledger_currency(self.uuid, self.payload, SimpleNamespace(), object())
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(raised.exception.detail, detail)

    def test_read_update_and_delete_translate_errors(self) -> None:
        cases = (
            ("get_currency", get_ledger_currency, CurrencyNotFoundError, 404, "Currency not found"),
            ("update_currency", update_ledger_currency, CurrencyNotFoundError, 404, "Currency not found"),
            ("update_currency", update_ledger_currency, CurrencyNameUnavailableError, 409, "Currency name unavailable"),
            ("delete_currency", delete_ledger_currency, CurrencyNotFoundError, 404, "Currency not found"),
            ("delete_currency", delete_ledger_currency, CurrencyInUseError, 409, "Currency is in use"),
        )
        for dependency, route, error, status_code, detail in cases:
            with self.subTest(dependency=dependency), patch(f"app.api.ledger.routes.currency.{dependency}", side_effect=error):
                with self.assertRaises(HTTPException) as raised:
                    if route is update_ledger_currency:
                        route(self.uuid, self.uuid, self.payload, SimpleNamespace(), object())
                    else:
                        route(self.uuid, self.uuid, SimpleNamespace(), object())
            self.assertEqual(raised.exception.status_code, status_code)
            self.assertEqual(raised.exception.detail, detail)
