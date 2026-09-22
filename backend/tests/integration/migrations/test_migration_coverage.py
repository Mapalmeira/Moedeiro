import unittest
from pathlib import Path


BACKEND_DIRECTORY = Path(__file__).resolve().parents[3]
MIGRATIONS_ROOT = BACKEND_DIRECTORY / "app/infrastructure/persistence/sqlite"
TESTS_DIRECTORY = Path(__file__).resolve().parent


class MigrationCoverageTest(unittest.TestCase):
    def test_every_sql_migration_has_a_dedicated_test_module(self) -> None:
        missing_tests: list[str] = []
        for database in ("registry", "ledger"):
            migrations_directory = MIGRATIONS_ROOT / database / "schema/migrations"
            for migration in sorted(migrations_directory.glob("*.sql")):
                expected_test = TESTS_DIRECTORY / f"test_{database}_{migration.stem}.py"
                if not expected_test.is_file():
                    missing_tests.append(str(expected_test.relative_to(BACKEND_DIRECTORY)))

        self.assertEqual(missing_tests, [])
