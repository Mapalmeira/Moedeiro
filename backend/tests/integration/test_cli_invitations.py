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


class InvitationCliTest(unittest.TestCase):
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

    @patch("app.cli.time.time", return_value=100)
    @patch("app.application.registry.use_cases.user_invitation.secrets.token_bytes", return_value=bytes(range(10)))
    def test_create_prints_relative_registration_link_and_persists_one_hour_expiration(self, token_bytes, current_time) -> None:
        output = StringIO()

        with redirect_stdout(output):
            exit_code = main(["invitation", "create"], self.settings)

        self.assertEqual(exit_code, 0)
        self.assertEqual(output.getvalue(), "/registration#invite=000G40R40M30E209\n")
        databases = self.create_databases()
        with databases.open_registry() as unit_of_work:
            invitations = unit_of_work.user_invitation_repository.list_all()
        self.assertEqual(len(invitations), 1)
        self.assertEqual(invitations[0].created_at, 100)
        self.assertEqual(invitations[0].expires_at, 3700)

    @patch("app.cli.time.time", return_value=100)
    def test_list_and_revoke_expose_invitation_state(self, current_time) -> None:
        with redirect_stdout(StringIO()):
            main(["invitation", "create", "--expiration-seconds", "120"], self.settings)
        databases = self.create_databases()
        with databases.open_registry() as unit_of_work:
            invitation = unit_of_work.user_invitation_repository.list_all()[0]

        active_output = StringIO()
        with redirect_stdout(active_output):
            self.assertEqual(main(["invitation", "list"], self.settings), 0)
        self.assertEqual(active_output.getvalue(), f"{invitation.uuid}\tACTIVE\t100\t220\n")

        revoke_output = StringIO()
        with redirect_stdout(revoke_output):
            self.assertEqual(main(["invitation", "revoke", str(invitation.uuid)], self.settings), 0)
        self.assertEqual(revoke_output.getvalue(), f"Revoked invitation {invitation.uuid}\n")

        revoked_output = StringIO()
        with redirect_stdout(revoked_output):
            self.assertEqual(main(["invitation", "list"], self.settings), 0)
        self.assertEqual(revoked_output.getvalue(), f"{invitation.uuid}\tREVOKED\t100\t220\n")

    def create_databases(self) -> SqliteDatabases:
        databases = SqliteDatabases(self.settings.registry_db_path, self.settings.registry_schema_path, self.settings.ledger_dbs_dir, self.settings.ledger_schema_path)
        databases.initialize()
        return databases


if __name__ == "__main__":
    unittest.main()
