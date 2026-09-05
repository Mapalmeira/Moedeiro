import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.registry.model.user_preferences import UserPreferences


class UserPreferencesTest(unittest.TestCase):
    def test_uses_defaults_when_preferences_are_omitted(self) -> None:
        preferences = UserPreferences(user_uuid=uuid4())

        self.assertEqual(preferences.language, "pt-BR")
        self.assertEqual(preferences.date_format, "DMY")
        self.assertEqual(preferences.time_format, "H24")
        self.assertEqual(preferences.number_format, "COMMA")
        self.assertEqual(preferences.theme, "LIGHT")
        self.assertEqual(preferences.timezone, "UTC")

    def test_accepts_all_supported_preferences(self) -> None:
        preferences = UserPreferences(user_uuid=uuid4(), language="pt-BR", date_format="DMY", time_format="H24", number_format="COMMA", theme="DARK", timezone="America/Fortaleza")

        self.assertEqual(preferences.language, "pt-BR")
        self.assertEqual(preferences.theme, "DARK")
        self.assertEqual(preferences.timezone, "America/Fortaleza")

    def test_rejects_unsupported_enumerated_preferences(self) -> None:
        for values in ({"language": "pt"}, {"date_format": "DD/MM/YYYY"}, {"time_format": "HH:mm"}, {"number_format": "pt-BR"}, {"theme": "SYSTEM"}, {"language": None}, {"date_format": None}, {"time_format": None}, {"number_format": None}, {"theme": None}, {"timezone": None}):
            with self.subTest(values=values):
                with self.assertRaises(ValidationError):
                    UserPreferences(user_uuid=uuid4(), **values)

    def test_enforces_text_limits(self) -> None:
        invalid_values = ({"timezone": ""}, {"timezone": "Unknown/Timezone"}, {"timezone": "x" * 51})
        for values in invalid_values:
            with self.subTest(values=values):
                with self.assertRaises(ValidationError):
                    UserPreferences(user_uuid=uuid4(), **values)

if __name__ == "__main__":
    unittest.main()
