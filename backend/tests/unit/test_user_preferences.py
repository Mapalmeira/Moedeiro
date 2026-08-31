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

if __name__ == "__main__":
    unittest.main()
