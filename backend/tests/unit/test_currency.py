"""Unit tests for the currency model."""

import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.ledger.model.currency import Currency


class CurrencyTest(unittest.TestCase):
    def test_accepts_optional_prefix_and_suffix(self) -> None:
        without_symbols = Currency(
            uuid=uuid4(),
            name="Real",
            decimal_places=2,
            icon="R$",
            color_code=b"\x80\x80\x80",
        )
        with_symbols = Currency(
            uuid=uuid4(),
            name="Real",
            prefix="R$",
            suffix="BRL",
            decimal_places=2,
            icon="R$",
            color_code=b"\x80\x80\x80",
        )

        self.assertIsNone(without_symbols.prefix)
        self.assertIsNone(without_symbols.suffix)
        self.assertEqual(with_symbols.prefix, "R$")
        self.assertEqual(with_symbols.suffix, "BRL")
        self.assertEqual(with_symbols.icon, "R$")

    def test_accepts_decimal_place_boundaries(self) -> None:
        for decimal_places in (0, 20):
            with self.subTest(decimal_places=decimal_places):
                currency = Currency(
                    uuid=uuid4(),
                    name="Currency",
                    decimal_places=decimal_places,
                    icon="$",
                    color_code=b"\x80\x80\x80",
                )
                self.assertEqual(currency.decimal_places, decimal_places)

    def test_rejects_decimal_places_outside_limits(self) -> None:
        for decimal_places in (-1, 21):
            with self.subTest(decimal_places=decimal_places):
                with self.assertRaises(ValidationError):
                    Currency(
                        uuid=uuid4(),
                        name="Currency",
                        decimal_places=decimal_places,
                        icon="$",
                        color_code=b"\x80\x80\x80",
                    )

    def test_rejects_name_outside_length_limits(self) -> None:
        for name in ("", "x" * 31):
            with self.subTest(name_length=len(name)):
                with self.assertRaises(ValidationError):
                    Currency(uuid=uuid4(), name=name, decimal_places=2, icon="$", color_code=b"\x80\x80\x80")

    def test_rejects_prefix_or_suffix_longer_than_limit(self) -> None:
        for field in ("prefix", "suffix"):
            values = {
                "uuid": uuid4(),
                "name": "Currency",
                "decimal_places": 2,
                "icon": "$",
                "color_code": b"\x80\x80\x80",
                field: "x" * 11,
            }

            with self.subTest(field=field):
                with self.assertRaises(ValidationError):
                    Currency.model_validate(values)

    def test_rejects_icon_or_color_outside_limits(self) -> None:
        invalid_values = (("icon", ""), ("icon", "x" * 51), ("color_code", b"\x00\x00"), ("color_code", b"\x00" * 4))
        for field, value in invalid_values:
            with self.subTest(field=field, length=len(value)):
                values = {"uuid": uuid4(), "name": "Currency", "decimal_places": 2, "icon": "$", "color_code": b"\x80\x80\x80"}
                values[field] = value
                with self.assertRaises(ValidationError):
                    Currency(**values)


if __name__ == "__main__":
    unittest.main()
