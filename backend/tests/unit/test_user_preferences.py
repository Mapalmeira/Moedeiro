import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.registry.model.user_preferences import UserPreferences


class UserPreferencesTest(unittest.TestCase):
    def test_accepts_empty_preferences(self) -> None:
        preferences = UserPreferences(user_uuid=uuid4())

        self.assertIsNone(preferences.date_format)
        self.assertIsNone(preferences.time_format)
        self.assertIsNone(preferences.number_format)
        self.assertIsNone(preferences.theme)
        self.assertIsNone(preferences.timezone)

    def test_accepts_all_supported_preferences(self) -> None:
        preferences = UserPreferences(user_uuid=uuid4(), date_format="DD/MM/YYYY", time_format="HH:mm", number_format="pt-BR", theme="DARK", timezone="America/Fortaleza")

        self.assertEqual(preferences.theme, "DARK")
        self.assertEqual(preferences.timezone, "America/Fortaleza")

    def test_rejects_unsupported_theme(self) -> None:
        with self.assertRaises(ValidationError):
            UserPreferences(user_uuid=uuid4(), theme="SYSTEM")

    def test_enforces_text_limits(self) -> None:
        invalid_values = ({"date_format": ""}, {"time_format": ""}, {"number_format": ""}, {"timezone": ""})
        for values in invalid_values:
            with self.subTest(values=values):
                with self.assertRaises(ValidationError):
                    UserPreferences(user_uuid=uuid4(), **values)

    def test_timezone_has_no_maximum_length(self) -> None:
        timezone = "x" * 10000

        preferences = UserPreferences(user_uuid=uuid4(), timezone=timezone)

        self.assertEqual(preferences.timezone, timezone)

    def test_formats_have_no_maximum_length(self) -> None:
        value = "x" * 10000

        preferences = UserPreferences(user_uuid=uuid4(), date_format=value, time_format=value, number_format=value)

        self.assertEqual(preferences.date_format, value)
        self.assertEqual(preferences.time_format, value)
        self.assertEqual(preferences.number_format, value)


if __name__ == "__main__":
    unittest.main()
