from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from app.application.registry.exceptions import UserNotFoundError
from app.application.registry.use_cases.user_preferences import get_user_preferences, save_user_preferences
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.registry.unit_of_work import SqliteRegistryUnitOfWork


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"


class UserPreferencesUseCasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.database = SqliteDatabase.initialize(Path(self.temporary_directory.name) / "registry.sqlite", SCHEMA_PATH)
        with self.open_registry() as unit_of_work:
            self.user = unit_of_work.user_repository.create("Alice", "$argon2id$test", 10)
            unit_of_work.commit()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def open_registry(self) -> SqliteRegistryUnitOfWork:
        return SqliteRegistryUnitOfWork(self.database)

    def test_get_returns_empty_preferences_until_the_user_saves_them(self) -> None:
        preferences = get_user_preferences(self.open_registry, self.user.uuid)

        self.assertEqual(preferences.user_uuid, self.user.uuid)
        self.assertIsNone(preferences.date_format)
        self.assertIsNone(preferences.theme)

    def test_save_replaces_the_complete_preference_set(self) -> None:
        saved = save_user_preferences(self.open_registry, self.user.uuid, "DD/MM/YYYY", "HH:mm", "pt-BR", "DARK", "America/Fortaleza")
        replaced = save_user_preferences(self.open_registry, self.user.uuid, None, "h:mm a", "1,234.56", "LIGHT", "America/New_York")

        self.assertEqual(saved.theme, "DARK")
        self.assertIsNone(replaced.date_format)
        self.assertEqual(get_user_preferences(self.open_registry, self.user.uuid), replaced)

    def test_save_rejects_an_unknown_user(self) -> None:
        with self.assertRaises(UserNotFoundError):
            save_user_preferences(self.open_registry, uuid4(), None, None, None, None, None)


if __name__ == "__main__":
    unittest.main()
