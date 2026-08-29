"""Unit tests for the account model."""

import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.ledger.model.account import Account


class AccountTest(unittest.TestCase):
    def test_accepts_valid_account_with_optional_note(self) -> None:
        account = Account(
            uuid=uuid4(),
            name="Checking",
            note=None,
            currency_uuid=uuid4(),
        )

        self.assertEqual(account.name, "Checking")
        self.assertIsNone(account.note)

    def test_rejects_name_outside_length_limits(self) -> None:
        for name in ("", "x" * 51):
            with self.subTest(name_length=len(name)):
                with self.assertRaises(ValidationError):
                    Account(
                        uuid=uuid4(),
                        name=name,
                        currency_uuid=uuid4(),
                    )

    def test_accepts_name_at_maximum_length(self) -> None:
        account = Account(uuid=uuid4(), name="x" * 50, currency_uuid=uuid4())

        self.assertEqual(len(account.name), 50)

    def test_rejects_note_longer_than_limit(self) -> None:
        with self.assertRaises(ValidationError):
            Account(
                uuid=uuid4(),
                name="Checking",
                note="x" * 301,
                currency_uuid=uuid4(),
            )


if __name__ == "__main__":
    unittest.main()
