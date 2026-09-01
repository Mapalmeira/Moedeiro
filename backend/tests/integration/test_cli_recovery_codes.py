from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.cli import main
from app.infrastructure.persistence.sqlite.databases import SqliteDatabases
from app.settings import Settings


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class RecoveryCodeCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        directory = Path(self.temporary_directory.name)
        self.settings = Settings(
            registry_schema_path=REGISTRY_SCHEMA_PATH,
            ledger_schema_path=LEDGER_SCHEMA_PATH,
            registry_db_path=directory / "registry/registry.sqlite",
            ledger_dbs_dir=directory / "ledgers",
        )
        databases = self.create_databases()
        with databases.open_registry() as unit_of_work:
            self.user = unit_of_work.user_repository.create("Alice", "$argon2id$test$password", 10)
            unit_of_work.commit()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @patch("app.cli.time.time", return_value=100)
    @patch("app.application.registry.use_cases.password.secrets.token_bytes", return_value=bytes(range(10)))
    def test_create_prints_a_relative_recovery_link_and_persists_the_code(self, token_bytes, current_time) -> None:
        output = StringIO()

        with redirect_stdout(output):
            exit_code = main(["recovery-code", "create", str(self.user.uuid)], self.settings)

        self.assertEqual(exit_code, 0)
        self.assertEqual(output.getvalue(), "/recover#code=000G40R40M30E209\n")
        databases = self.create_databases()
        with databases.open_registry() as unit_of_work:
            codes = unit_of_work.recovery_code_repository.list_by_user(self.user.uuid)
        self.assertEqual(len(codes), 1)
        self.assertEqual(codes[0].created_at, 100)

    @patch("app.cli.time.time", return_value=100)
    def test_list_and_revoke_expose_recovery_code_state(self, current_time) -> None:
        with redirect_stdout(StringIO()):
            main(["recovery-code", "create", str(self.user.uuid)], self.settings)
        databases = self.create_databases()
        with databases.open_registry() as unit_of_work:
            recovery_code = unit_of_work.recovery_code_repository.list_by_user(self.user.uuid)[0]

        active_output = StringIO()
        with redirect_stdout(active_output):
            self.assertEqual(main(["recovery-code", "list", str(self.user.uuid)], self.settings), 0)
        self.assertEqual(active_output.getvalue(), f"{recovery_code.uuid}\tACTIVE\t100\n")

        revoke_output = StringIO()
        with redirect_stdout(revoke_output):
            self.assertEqual(main(["recovery-code", "revoke", str(recovery_code.uuid)], self.settings), 0)
        self.assertEqual(revoke_output.getvalue(), f"Revoked recovery code {recovery_code.uuid}\n")

        revoked_output = StringIO()
        with redirect_stdout(revoked_output):
            self.assertEqual(main(["recovery-code", "list", str(self.user.uuid)], self.settings), 0)
        self.assertEqual(revoked_output.getvalue(), f"{recovery_code.uuid}\tREVOKED\t100\n")

    def test_create_rejects_an_unknown_user(self) -> None:
        from uuid import uuid4

        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(["recovery-code", "create", str(uuid4())], self.settings)

        self.assertEqual(exit_code, 1)
        self.assertEqual(output.getvalue(), "User not found\n")

    def create_databases(self) -> SqliteDatabases:
        databases = SqliteDatabases(self.settings.registry_db_path, self.settings.registry_schema_path, self.settings.ledger_dbs_dir, self.settings.ledger_schema_path)
        databases.initialize()
        return databases


if __name__ == "__main__":
    unittest.main()
