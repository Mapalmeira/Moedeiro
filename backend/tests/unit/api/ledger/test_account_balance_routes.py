from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException

from app.api.ledger.routes.account_balance import list_ledger_account_balances
from app.application.ledger.exceptions import CurrencyNotFoundError


class AccountBalanceRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.uuid = uuid4()
        self.request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace(max_page_size=50))))

    def test_list_validates_limit_and_translates_unknown_currency(self) -> None:
        with patch("app.api.ledger.routes.account_balance.validate_page_size") as validate, patch(
            "app.api.ledger.routes.account_balance.ledger_unit_of_work_factory", return_value=object()
        ), patch("app.api.ledger.routes.account_balance.list_account_balances", side_effect=CurrencyNotFoundError):
            with self.assertRaises(HTTPException) as raised:
                list_ledger_account_balances(self.uuid, 10, self.request, object(), self.uuid, 5)

        validate.assert_called_once_with(self.request, 5)
        self.assertEqual((raised.exception.status_code, raised.exception.detail), (404, "Currency not found"))

    def test_list_allows_an_omitted_limit(self) -> None:
        with patch("app.api.ledger.routes.account_balance.validate_page_size") as validate, patch(
            "app.api.ledger.routes.account_balance.ledger_unit_of_work_factory", return_value=object()
        ), patch("app.api.ledger.routes.account_balance.list_account_balances", return_value=([], None)):
            response = list_ledger_account_balances(self.uuid, 10, self.request, object())

        validate.assert_not_called()
        self.assertEqual(response.items, [])
        self.assertIsNone(response.total_balance)
