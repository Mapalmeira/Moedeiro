from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi import Request
from pydantic import ValidationError

from app.api.registry.routes.user_preferences import get_preferences, save_preferences
from app.api.registry.schema.user_preferences import UserPreferencesPayload
from app.factory import create_app
from app.settings import Settings
from tests.fakes import FakeCredentialOperationExecutor, FakePasswordHasher, FakeRateLimiter, FakeTotpAuthenticator


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class UserPreferencesRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        directory = Path(self.temporary_directory.name)
        self.application = create_app(
            Settings(
                registry_schema_path=REGISTRY_SCHEMA_PATH,
                ledger_schema_path=LEDGER_SCHEMA_PATH,
                registry_db_path=directory / "registry/registry.sqlite",
                ledger_dbs_dir=directory / "ledgers",
            ),
            FakePasswordHasher(),
            FakeRateLimiter(),
            FakeTotpAuthenticator(),
            FakeCredentialOperationExecutor(),
        )
        with self.application.state.databases.open_registry() as unit_of_work:
            self.user = unit_of_work.user_repository.create("Alice", "$argon2id$test", 10)
            unit_of_work.commit()
        self.request = Request({"type": "http", "app": self.application, "client": ("192.0.2.1", 50000), "headers": []})

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_get_returns_empty_preferences_before_the_first_save(self) -> None:
        preferences = get_preferences(self.request, self.user)

        self.assertIsNone(preferences.date_format)
        self.assertIsNone(preferences.timezone)

    def test_put_replaces_preferences_and_get_returns_the_saved_values(self) -> None:
        saved = save_preferences(
            UserPreferencesPayload(
                date_format="DMY",
                time_format="H24",
                number_format="COMMA",
                theme="DARK",
                timezone="America/Fortaleza",
            ),
            self.request,
            self.user,
        )
        replaced = save_preferences(UserPreferencesPayload(theme="LIGHT"), self.request, self.user)

        self.assertEqual(saved.theme, "DARK")
        self.assertIsNone(replaced.date_format)
        self.assertEqual(get_preferences(self.request, self.user), replaced)

    def test_request_rejects_an_invalid_theme_or_empty_format(self) -> None:
        for values in ({"theme": "SYSTEM"}, {"date_format": "DD/MM/YYYY"}, {"timezone": "Unknown/Timezone"}):
            with self.subTest(values=values):
                with self.assertRaises(ValidationError):
                    UserPreferencesPayload(**values)

    def test_routes_are_exposed(self) -> None:
        operations = self.application.openapi()["paths"]["/api/user/preferences"]

        self.assertIn("200", operations["get"]["responses"])
        self.assertIn("200", operations["put"]["responses"])


if __name__ == "__main__":
    unittest.main()
