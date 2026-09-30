import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import HTTPException

from app.api.ledger.routes.account import delete_ledger_account
from app.api.ledger.routes.account_balance import list_ledger_account_balances
from app.api.registry.routes.user_preferences import save_preferences
from app.api.registry.routes.authentication import refresh
from app.api.registry.routes.ledger import create_owned_ledger
from app.api.registry.routes.registration import create_user
from app.application.ledger.exceptions import AccountInUseError, AccountNotFoundError, CurrencyNotFoundError
from app.application.registry.exceptions import InvitationNotAvailableError, UserNotFoundError


class RemainingRoutesTest(unittest.TestCase):
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
        self.user = SimpleNamespace(uuid=self.uuid)

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

    def test_balance_list_validates_limit_and_translates_unknown_currency(self) -> None:
        with patch("app.api.ledger.routes.account_balance.validate_page_size") as validate, patch(
            "app.api.ledger.routes.account_balance.ledger_unit_of_work_factory", return_value=object()
        ), patch("app.api.ledger.routes.account_balance.list_account_balances", side_effect=CurrencyNotFoundError):
            with self.assertRaises(HTTPException) as raised:
                list_ledger_account_balances(self.uuid, 10, self.request, object(), self.uuid, 5)

        validate.assert_called_once_with(self.request, 5)
        self.assertEqual((raised.exception.status_code, raised.exception.detail), (404, "Currency not found"))

    def test_balance_list_allows_an_omitted_limit(self) -> None:
        with patch("app.api.ledger.routes.account_balance.validate_page_size") as validate, patch(
            "app.api.ledger.routes.account_balance.ledger_unit_of_work_factory", return_value=object()
        ), patch("app.api.ledger.routes.account_balance.list_account_balances", return_value=([], None)):
            response = list_ledger_account_balances(self.uuid, 10, self.request, object())

        validate.assert_not_called()
        self.assertEqual(response.items, [])
        self.assertIsNone(response.total_balance)

    def test_preferences_save_rejects_a_deleted_user(self) -> None:
        payload = SimpleNamespace(language="pt-BR", theme="SYSTEM")
        with patch("app.api.registry.routes.user_preferences.save_user_preferences", side_effect=UserNotFoundError):
            with self.assertRaises(HTTPException) as raised:
                save_preferences(payload, self.request, self.user)

        self.assertEqual((raised.exception.status_code, raised.exception.detail), (401, "Invalid session"))

    def test_refresh_rejects_a_missing_remember_cookie(self) -> None:
        request = SimpleNamespace(
            cookies={},
            app=SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace(refresh_ip_attempts_rate_limit="1/minute"))),
        )
        with patch("app.api.registry.routes.authentication.check_rate_limit"):
            with self.assertRaises(HTTPException) as raised:
                refresh(request, SimpleNamespace())
        self.assertEqual((raised.exception.status_code, raised.exception.detail), (401, "Invalid session"))

    def test_ledger_creation_rejects_a_deleted_authenticated_user(self) -> None:
        databases = SimpleNamespace(open_registry=object(), initialize_ledger=object(), delete_ledger_database=object())
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(databases=databases)))
        payload = SimpleNamespace(name="Ledger", icon="lucide:BookOpen", color_code="#808080")
        with patch("app.api.registry.routes.ledger.create_ledger", side_effect=UserNotFoundError):
            with self.assertRaises(HTTPException) as raised:
                create_owned_ledger(payload, request, self.user)
        self.assertEqual((raised.exception.status_code, raised.exception.detail), (401, "Invalid session"))

    def test_registration_translates_a_concurrently_consumed_invitation(self) -> None:
        request = SimpleNamespace(
            app=SimpleNamespace(
                state=SimpleNamespace(
                    settings=SimpleNamespace(registration_ip_attempts_rate_limit="1/minute"),
                    databases=SimpleNamespace(open_registry=object()),
                )
            )
        )
        payload = SimpleNamespace(invitation_code="0" * 16, name="Alice", password="valid password")
        with patch("app.api.registry.routes.registration.check_rate_limit"), patch(
            "app.api.registry.routes.registration.execute_credential_operation",
            new=AsyncMock(side_effect=InvitationNotAvailableError),
        ):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(create_user(payload, request))
        self.assertEqual((raised.exception.status_code, raised.exception.detail), (404, "Invitation not available"))
