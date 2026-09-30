from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException

from app.api.ledger.routes.account import delete_ledger_account
from app.application.ledger.exceptions import AccountInUseError, AccountNotFoundError


class AccountRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.uuid = uuid4()
        self.request = SimpleNamespace(
            app=SimpleNamespace(
                state=SimpleNamespace(
                    settings=SimpleNamespace(max_page_size=50),
                    databases=SimpleNamespace(open_registry=object()),
                )
            )
        )

    def test_account_deletion_translates_domain_errors(self) -> None:
        for error, status_code, detail in (
            (AccountNotFoundError, 404, "Account not found"),
            (AccountInUseError, 409, "Account is in use"),
        ):
            with self.subTest(error=error), patch("app.api.ledger.routes.account.ledger_unit_of_work_factory", return_value=object()), patch(
                "app.api.ledger.routes.account.delete_account", side_effect=error
            ):
                with self.assertRaises(HTTPException) as raised:
                    delete_ledger_account(self.uuid, self.uuid, self.request, object())
            self.assertEqual((raised.exception.status_code, raised.exception.detail), (status_code, detail))
