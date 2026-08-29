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
            icon="WalletCards",
            color_code=b"\x80\x80\x80",
        )

        self.assertEqual(account.name, "Checking")
        self.assertIsNone(account.note)
        self.assertEqual(account.icon, "WalletCards")
        self.assertEqual(account.color_code, b"\x80\x80\x80")

    def test_rejects_name_outside_length_limits(self) -> None:
        for name in ("", "x" * 51):
            with self.subTest(name_length=len(name)):
                with self.assertRaises(ValidationError):
                    Account(
                        uuid=uuid4(),
                        name=name,
                        currency_uuid=uuid4(),
                        icon="WalletCards",
                        color_code=b"\x80\x80\x80",
                    )

    def test_accepts_name_at_maximum_length(self) -> None:
        account = Account(uuid=uuid4(), name="x" * 50, currency_uuid=uuid4(), icon="WalletCards", color_code=b"\x80\x80\x80")

        self.assertEqual(len(account.name), 50)

    def test_rejects_note_longer_than_limit(self) -> None:
        with self.assertRaises(ValidationError):
            Account(
                uuid=uuid4(),
                name="Checking",
                note="x" * 301,
                currency_uuid=uuid4(),
                icon="WalletCards",
                color_code=b"\x80\x80\x80",
            )

    def test_rejects_icon_or_color_outside_limits(self) -> None:
        invalid_values = (("icon", ""), ("icon", "x" * 51), ("color_code", b"\x00\x00"), ("color_code", b"\x00" * 4))
        for field, value in invalid_values:
            with self.subTest(field=field, length=len(value)):
                values = {"uuid": uuid4(), "name": "Checking", "currency_uuid": uuid4(), "icon": "WalletCards", "color_code": b"\x80\x80\x80"}
                values[field] = value
                with self.assertRaises(ValidationError):
                    Account(**values)


if __name__ == "__main__":
    unittest.main()
