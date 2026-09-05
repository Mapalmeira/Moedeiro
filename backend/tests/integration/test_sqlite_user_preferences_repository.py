import sqlite3
from uuid import uuid4

from tests.integration.registry_repository_test_case import RegistryRepositoryTestCase


class SqliteUserPreferencesRepositoryTest(RegistryRepositoryTestCase):
    def test_save_creates_preferences(self) -> None:
        user = self.create_user()

        preferences = self.preferences_repository.save(user.uuid, "pt-BR", "DMY", "H24", "COMMA", "LIGHT", "UTC")

        self.assertEqual(self.preferences_repository.get(user.uuid), preferences)

    def test_save_replaces_all_preferences_for_existing_user(self) -> None:
        user = self.create_user()
        self.preferences_repository.save(user.uuid, "pt-BR", "DMY", "H24", "COMMA", "LIGHT", "America/Fortaleza")

        updated = self.preferences_repository.save(user.uuid, "en", "MDY", "H12", "DOT", "DARK", "America/New_York")

        self.assertEqual(self.preferences_repository.get(user.uuid), updated)
        self.assertEqual(updated.language, "en")
        self.assertEqual(updated.time_format, "H12")

    def test_save_requires_an_existing_user(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.preferences_repository.save(uuid4(), "pt-BR", "DMY", "H24", "COMMA", "LIGHT", "UTC")

    def test_get_returns_none_without_saved_preferences(self) -> None:
        self.assertIsNone(self.preferences_repository.get(self.create_user().uuid))


if __name__ == "__main__":
    import unittest

    unittest.main()
