from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.application.registry.use_cases.cleanup import SECONDS_PER_DAY
from app.cli import main
from app.infrastructure.persistence.sqlite.databases import SqliteDatabases
from app.settings import Settings


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class CleanupCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        directory = Path(self.temporary_directory.name)
        self.settings = Settings(
            registry_schema_path=REGISTRY_SCHEMA_PATH,
            ledger_schema_path=LEDGER_SCHEMA_PATH,
            registry_db_path=directory / "registry/registry.sqlite",
            ledger_dbs_dir=directory / "ledgers",
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @patch("app.cli.time.time", return_value=100 * SECONDS_PER_DAY)
    def test_removes_records_inactive_at_the_retention_cutoff(self, current_time) -> None:
        databases = SqliteDatabases(self.settings.registry_db_path, self.settings.registry_schema_path, self.settings.ledger_dbs_dir, self.settings.ledger_schema_path)
        databases.initialize()
        with databases.open_registry() as unit_of_work:
            invitation = unit_of_work.user_invitation_repository.create(b"i" * 32, 1, 100 * SECONDS_PER_DAY)
            unit_of_work.user_invitation_repository.consume(invitation.uuid, 70 * SECONDS_PER_DAY)
            unit_of_work.commit()

        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(["cleanup", "--days", "30"], self.settings)

        self.assertEqual(exit_code, 0)
        self.assertEqual(output.getvalue(), "Removed 1 inactive records\n")


if __name__ == "__main__":
    unittest.main()
