from contextlib import redirect_stdout
import hashlib
import time
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

from app.cli import main
from app.infrastructure.persistence.sqlite.databases import SqliteDatabases
from app.settings import Settings
from tests.fakes import FakePasswordHasher


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class UserDeletionCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        directory = Path(self.temporary_directory.name)
        self.settings = Settings(
            registry_schema_path=REGISTRY_SCHEMA_PATH,
            ledger_schema_path=LEDGER_SCHEMA_PATH,
            registry_db_path=directory / "registry/registry.sqlite",
            ledger_dbs_dir=directory / "ledgers",
        )
        self.databases = SqliteDatabases(self.settings.registry_db_path, self.settings.registry_schema_path, self.settings.ledger_dbs_dir, self.settings.ledger_schema_path)
        self.databases.initialize()
        owned_ledger_uuid = uuid4()
        revoked_ledger_uuid = uuid4()
        owned_ledger_path = self.databases.initialize_ledger(owned_ledger_uuid, 10, "pt-BR")
        revoked_ledger_path = self.databases.initialize_ledger(revoked_ledger_uuid, 10, "pt-BR")
        with self.databases.open_registry() as unit_of_work:
            self.user = unit_of_work.user_repository.create("Alice", "$argon2id$test", 10)
            self.owned_ledger = unit_of_work.ledger_repository.create(owned_ledger_uuid, "Owned", owned_ledger_path.name, "lucide:BookOpen", b"\x80\x80\x80", 10)
            self.revoked_ledger = unit_of_work.ledger_repository.create(revoked_ledger_uuid, "Revoked", revoked_ledger_path.name, "lucide:BookOpen", b"\x80\x80\x80", 10)
            unit_of_work.ledger_grant_repository.create(self.user.uuid, self.owned_ledger.uuid, "OWNER", 10)
            revoked_grant = unit_of_work.ledger_grant_repository.create(self.user.uuid, self.revoked_ledger.uuid, "OWNER", 10)
            unit_of_work.ledger_grant_repository.revoke(revoked_grant.uuid, 20)
            unit_of_work.mfa_method_repository.create(self.user.uuid, "TOTP", b"encrypted", 10, 610, 10)
            unit_of_work.recovery_code_repository.create(self.user.uuid, b"c" * 32, 10, 110)
            unit_of_work.user_preferences_repository.save(self.user.uuid, "pt-BR", "YMD", "H24", "DOT", "DARK", "UTC")
            unit_of_work.auth_session_repository.create(self.user.uuid, b"s" * 32, 10, 100, 10)
            unit_of_work.remember_session_repository.create(self.user.uuid, b"r" * 32, 10, 100)
            unit_of_work.commit()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_deletes_the_user_dependencies_and_active_owned_ledger_database(self) -> None:
        output = StringIO()

        with redirect_stdout(output):
            exit_code = main(["user", "delete", str(self.user.uuid)], self.settings)

        self.assertEqual(exit_code, 0)
        self.assertEqual(output.getvalue(), f"Deleted user {self.user.uuid} and 1 owned ledgers\n")
        self.assertFalse((self.databases.ledger_dbs_dir / self.owned_ledger.path).exists())
        self.assertTrue((self.databases.ledger_dbs_dir / self.revoked_ledger.path).exists())
        with self.databases.open_registry() as unit_of_work:
            self.assertIsNone(unit_of_work.user_repository.get(self.user.uuid))
            self.assertIsNone(unit_of_work.ledger_repository.get(self.owned_ledger.uuid))
            self.assertIsNotNone(unit_of_work.ledger_repository.get(self.revoked_ledger.uuid))
            self.assertEqual(unit_of_work.ledger_grant_repository.list_by_user(self.user.uuid), [])
            self.assertEqual(unit_of_work.mfa_method_repository.list_by_user(self.user.uuid), [])
            self.assertEqual(unit_of_work.recovery_code_repository.list_by_user(self.user.uuid), [])
            self.assertIsNone(unit_of_work.user_preferences_repository.get(self.user.uuid))
            self.assertEqual(unit_of_work.auth_session_repository.list_by_user(self.user.uuid), [])
            self.assertEqual(unit_of_work.remember_session_repository.list_by_user(self.user.uuid), [])

    def test_reports_a_missing_user_without_touching_ledgers(self) -> None:
        from uuid import uuid4

        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(["user", "delete", str(uuid4())], self.settings)

        self.assertEqual(exit_code, 1)
        self.assertEqual(output.getvalue(), "User not found\n")
        self.assertTrue((self.databases.ledger_dbs_dir / self.owned_ledger.path).is_file())

    @patch("app.cli.time.time", return_value=100)
    @patch("app.cli.Argon2PasswordHasher")
    @patch("app.cli.getpass.getpass", side_effect=["correct password", "correct password"])
    def test_create_then_list_are_convenient_admin_operations(self, get_password, password_hasher_class, current_time) -> None:
        password_hasher = FakePasswordHasher()
        password_hasher_class.return_value = password_hasher
        output = StringIO()

        with redirect_stdout(output):
            self.assertEqual(main(["user", "create", "Bob"], self.settings), 0)

        with self.databases.open_registry() as unit_of_work:
            user = unit_of_work.user_repository.get_by_normalized_name("bob")
        assert user is not None
        self.assertEqual(output.getvalue(), f"Created user {user.uuid}\n")
        self.assertEqual(password_hasher.passwords, ["correct password"])
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["user", "list"], self.settings), 0)
        self.assertIn(f"{user.uuid}\tBob\t100\n", output.getvalue())

    @patch("app.cli.time.time", return_value=100)
    def test_sets_ledger_owner_lists_grants_and_revokes_a_grant(self, current_time) -> None:
        with self.databases.open_registry() as unit_of_work:
            second_user = unit_of_work.user_repository.create("Bob", "$argon2id$test", 10)
            unit_of_work.commit()
        output = StringIO()

        with redirect_stdout(output):
            exit_code = main(["grant", "set-owner", str(second_user.uuid), str(self.owned_ledger.uuid)], self.settings)

        self.assertEqual(exit_code, 0)
        self.assertEqual(output.getvalue(), f"Set user {second_user.uuid} as owner of ledger {self.owned_ledger.uuid}\n")
        with self.databases.open_registry() as unit_of_work:
            new_grant = unit_of_work.ledger_grant_repository.get_active(second_user.uuid, self.owned_ledger.uuid)
        assert new_grant is not None
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(["grant", "list", str(second_user.uuid), str(self.owned_ledger.uuid)], self.settings)
        self.assertEqual(exit_code, 0)
        self.assertEqual(output.getvalue(), f"{new_grant.uuid}\t{second_user.uuid}\t{self.owned_ledger.uuid}\tOWNER\t100\t\n")
        with self.databases.open_registry() as unit_of_work:
            grant = unit_of_work.ledger_grant_repository.get_active(self.user.uuid, self.owned_ledger.uuid)
        self.assertIsNone(grant)
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(["grant", "revoke", str(new_grant.uuid)], self.settings)
        self.assertEqual(exit_code, 0)
        self.assertEqual(output.getvalue(), f"Revoked ledger grant {new_grant.uuid}\n")

    @patch("app.cli.time.time", return_value=100)
    @patch("app.domain.registry.model.crockford_code.secrets.token_bytes", return_value=bytes(range(10)))
    def test_recover_password_emits_a_code_without_exposing_recovery_code_administration(self, token_bytes, current_time) -> None:
        output = StringIO()

        with redirect_stdout(output):
            self.assertEqual(main(["user", "recover-password", str(self.user.uuid)], self.settings), 0)

        code = output.getvalue().strip()
        self.assertEqual(len(code), 16)
        with self.databases.open_registry() as unit_of_work:
            recovery_code = unit_of_work.recovery_code_repository.get_active_by_user(self.user.uuid, 20)
        assert recovery_code is not None
        self.assertEqual(recovery_code.code_hash, hashlib.sha256(code.encode("ascii")).digest())
        self.assertEqual(recovery_code.expires_at, current_time.return_value + 3_600)

    def test_recover_password_accepts_a_custom_expiration(self) -> None:
        output = StringIO()

        with redirect_stdout(output):
            self.assertEqual(main(["user", "recover-password", str(self.user.uuid), "--expiration-seconds", "120"], self.settings), 0)

        with self.databases.open_registry() as unit_of_work:
            recovery_code = unit_of_work.recovery_code_repository.get_active_by_user(self.user.uuid, int(time.time()))
        assert recovery_code is not None
        self.assertEqual(recovery_code.expires_at - recovery_code.created_at, 120)

    def test_disable_mfa_removes_methods_and_sessions_but_preserves_recovery_code(self) -> None:
        output = StringIO()

        with redirect_stdout(output):
            self.assertEqual(main(["user", "disable-mfa", str(self.user.uuid)], self.settings), 0)

        self.assertEqual(output.getvalue(), f"Disabled MFA for user {self.user.uuid}\n")
        with self.databases.open_registry() as unit_of_work:
            self.assertEqual(unit_of_work.mfa_method_repository.list_by_user(self.user.uuid), [])
            self.assertEqual(unit_of_work.auth_session_repository.list_by_user(self.user.uuid), [])
            self.assertEqual(unit_of_work.remember_session_repository.list_by_user(self.user.uuid), [])
            self.assertIsNotNone(unit_of_work.recovery_code_repository.get_active_by_user(self.user.uuid, 20))


if __name__ == "__main__":
    unittest.main()
