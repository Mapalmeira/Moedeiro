import argparse
from contextlib import contextmanager, redirect_stdout
from io import StringIO
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID

from app.application.registry.exceptions import ExternalAccessNotFoundError, LedgerGrantNotFoundError, LedgerLimitReachedError, LedgerNotFoundError, LedgerOwnershipAlreadyExistsError, UserNameUnavailableError, UserNotFoundError
from app.cli import _create_recovery_code, _create_user, _delete_external_access, _delete_user, _disable_mfa, _nonnegative_int, _port, _positive_int, _revoke_invitation, _revoke_ledger_grant, _set_ledger_owner, _status
from app.domain.registry.model.user_invitation import UserInvitation


class CliCommandsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.databases = SimpleNamespace(open_registry=object(), delete_ledger_database=MagicMock())
        self.uuid = UUID("00000000-0000-0000-0000-000000000001")

    def test_revoke_invitation_reports_an_unavailable_invitation(self) -> None:
        with patch("app.cli.revoke_user_invitation", return_value=False), self.output() as output:
            result = _revoke_invitation(self.databases, self.uuid)

        self.assertEqual(result, 1)
        self.assertEqual(output.getvalue(), "Invitation not available\n")

    def test_recovery_code_reports_an_unknown_user(self) -> None:
        with patch("app.cli.create_recovery_code", side_effect=UserNotFoundError), self.output() as output:
            result = _create_recovery_code(self.databases, 100, self.uuid, 60)

        self.assertEqual(result, 1)
        self.assertEqual(output.getvalue(), "User not found\n")

    def test_create_user_rejects_mismatched_passwords(self) -> None:
        with patch("app.cli.getpass.getpass", side_effect=["first", "second"]), self.output() as output:
            self.assertEqual(_create_user(self.databases, "maria", 100), 1)
        self.assertEqual(output.getvalue(), "Passwords do not match\n")

    def test_create_user_reports_an_unavailable_name(self) -> None:
        with patch("app.cli.getpass.getpass", side_effect=["password", "password"]), patch("app.cli.create_user", side_effect=UserNameUnavailableError), self.output() as output:
            self.assertEqual(_create_user(self.databases, "maria", 100), 1)
        self.assertEqual(output.getvalue(), "User name unavailable\n")

    def test_external_access_deletion_reports_an_unknown_access(self) -> None:
        with patch("app.cli.delete_external_access", side_effect=ExternalAccessNotFoundError), self.output() as output:
            self.assertEqual(_delete_external_access(self.databases, self.uuid), 1)
        self.assertEqual(output.getvalue(), "External access not found\n")

    def test_set_ledger_owner_reports_domain_errors(self) -> None:
        cases = (
            (UserNotFoundError, "User not found"),
            (LedgerNotFoundError, "Ledger not found"),
            (LedgerOwnershipAlreadyExistsError, "User already owns ledger"),
            (LedgerLimitReachedError, "Ledger limit reached"),
        )
        for error, message in cases:
            with self.subTest(error=error), patch("app.cli.set_ledger_owner", side_effect=error), self.output() as output:
                self.assertEqual(_set_ledger_owner(self.databases, self.uuid, self.uuid, 100), 1)
            self.assertEqual(output.getvalue(), f"{message}\n")

    def test_grant_revocation_reports_an_unknown_grant(self) -> None:
        with patch("app.cli.revoke_ledger_grant", side_effect=LedgerGrantNotFoundError), self.output() as output:
            self.assertEqual(_revoke_ledger_grant(self.databases, self.uuid, 100), 1)
        self.assertEqual(output.getvalue(), "Active ledger grant not found\n")

    def test_user_deletion_reports_an_unknown_user(self) -> None:
        with patch("app.cli.delete_user", side_effect=UserNotFoundError), self.output() as output:
            self.assertEqual(_delete_user(self.databases, self.uuid), 1)
        self.assertEqual(output.getvalue(), "User not found\n")

    def test_disable_mfa_reports_an_unknown_user_or_missing_method(self) -> None:
        with patch("app.cli.disable_mfa", side_effect=UserNotFoundError), self.output() as output:
            self.assertEqual(_disable_mfa(self.databases, self.uuid), 1)
        self.assertEqual(output.getvalue(), "User not found\n")

        with patch("app.cli.disable_mfa", return_value=0), self.output() as output:
            self.assertEqual(_disable_mfa(self.databases, self.uuid), 1)
        self.assertEqual(output.getvalue(), "MFA not enabled\n")

    def test_invitation_status_distinguishes_active_expired_and_consumed(self) -> None:
        base = {"uuid": self.uuid, "secret_hash": b"x" * 32, "created_at": 10, "expires_at": 30}

        self.assertEqual(_status(UserInvitation(**base), 20), "ACTIVE")
        self.assertEqual(_status(UserInvitation(**base), 30), "EXPIRED")
        self.assertEqual(_status(UserInvitation(**base, consumed_at=20), 20), "CONSUMED")

    def test_numeric_cli_arguments_reject_values_outside_their_ranges(self) -> None:
        for parser, value in ((_port, "0"), (_port, "65536"), (_positive_int, "0"), (_nonnegative_int, "-1")):
            with self.subTest(parser=parser.__name__, value=value), self.assertRaises(argparse.ArgumentTypeError):
                parser(value)

        self.assertEqual(_port("8080"), 8080)
        self.assertEqual(_positive_int("1"), 1)
        self.assertEqual(_nonnegative_int("0"), 0)

    @contextmanager
    def output(self):
        output = StringIO()
        with redirect_stdout(output):
            yield output
