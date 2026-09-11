import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.registry.model.user_preferences import UserPreferences


VALID_PREFERENCES = {
    "language": "pt-BR",
    "theme": "LIGHT",
    "timezone": "UTC",
}


class UserPreferencesTest(unittest.TestCase):
    def test_requires_all_preferences(self) -> None:
        with self.assertRaises(ValidationError) as context:
            UserPreferences(user_uuid=uuid4())

        missing_fields = {error["loc"][0] for error in context.exception.errors() if error["type"] == "missing"}
        self.assertEqual(missing_fields, {"language", "theme", "timezone"})

    def test_accepts_all_supported_preferences(self) -> None:
        preferences = UserPreferences(
            user_uuid=uuid4(),
            language="pt-BR",
            theme="DARK",
            timezone="America/Fortaleza",
        )

        self.assertEqual(preferences.language, "pt-BR")
        self.assertEqual(preferences.theme, "DARK")
        self.assertEqual(preferences.timezone, "America/Fortaleza")

    def test_rejects_unsupported_preferences(self) -> None:
        invalid_overrides = (
            {"language": "pt"},
            {"theme": "SYSTEM"},
            {"language": None},
            {"theme": None},
            {"timezone": None},
        )
        for override in invalid_overrides:
            with self.subTest(override=override):
                with self.assertRaises(ValidationError):
                    UserPreferences(user_uuid=uuid4(), **(VALID_PREFERENCES | override))

    def test_enforces_timezone_validation(self) -> None:
        invalid_overrides = (
            {"timezone": ""},
            {"timezone": "Unknown/Timezone"},
            {"timezone": "x" * 51},
        )
        for override in invalid_overrides:
            with self.subTest(override=override):
                with self.assertRaises(ValidationError):
                    UserPreferences(user_uuid=uuid4(), **(VALID_PREFERENCES | override))


if __name__ == "__main__":
    unittest.main()
