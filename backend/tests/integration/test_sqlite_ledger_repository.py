"""Integration tests for the registry SQLite ledger repository."""

import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.domain.registry.model.auth_session import DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, DEFAULT_INACTIVITY_TIMEOUT_SECONDS
from app.domain.registry.model.user_invitation import DEFAULT_EXPIRATION_TIMEOUT_SECONDS
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.registry.repository.auth_session import SqliteAuthSessionRepository
from app.infrastructure.persistence.sqlite.registry.repository.ledger_grant import SqliteLedgerGrantRepository
from app.infrastructure.persistence.sqlite.registry.repository.ledger import SqliteLedgerRepository
from app.infrastructure.persistence.sqlite.registry.repository.user_invitation import SqliteUserInvitationRepository
from app.infrastructure.persistence.sqlite.registry.repository.user import SqliteUserRepository


SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
)


class SqliteLedgerRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "registry.sqlite"
        self.connection = SqliteDatabase(database_path).get_connection()
        self.connection.executescript(SCHEMA_PATH.read_text())
        self.repository = SqliteLedgerRepository(self.connection)

    def create_ledger(self, path: str):
        return self.repository.create("Main ledger", path, "BookOpen", b"\x80\x80\x80")

    def tearDown(self) -> None:
        self.connection.close()
        self.temporary_directory.cleanup()

    def test_create_can_be_read_by_uuid_and_path(self) -> None:
        """create persists a generated UUID and the supplied path."""
        ledger = self.create_ledger("ledger.sqlite")

        self.assertEqual(self.repository.get(ledger.uuid), ledger)
        self.assertEqual(self.repository.get_by_path("ledger.sqlite"), ledger)

    def test_get_returns_none_when_ledger_does_not_exist(self) -> None:
        """get and get_by_path represent an absent row with None."""
        self.create_ledger("ledger.sqlite")
        ledger = self.repository.get_by_path("ledger.sqlite")
        assert ledger is not None
        self.repository.delete(ledger.uuid)

        self.assertIsNone(self.repository.get(ledger.uuid))
        self.assertIsNone(self.repository.get_by_path("ledger.sqlite"))

    def test_update_path_changes_only_the_selected_ledger(self) -> None:
        """update_path keeps the UUID and changes only the requested row."""
        self.create_ledger("first.sqlite")
        self.create_ledger("second.sqlite")
        first = self.repository.get_by_path("first.sqlite")
        second = self.repository.get_by_path("second.sqlite")
        assert first is not None
        assert second is not None

        self.repository.update_path(first.uuid, "updated.sqlite")

        self.assertIsNone(self.repository.get_by_path("first.sqlite"))
        self.assertEqual(
            self.repository.get(first.uuid),
            first.model_copy(update={"path": "updated.sqlite"}),
        )
        self.assertEqual(self.repository.get(second.uuid), second)

    def test_update_name_changes_only_the_selected_ledger(self) -> None:
        ledger = self.create_ledger("ledger.sqlite")

        self.repository.update_name(ledger.uuid, "Household")

        updated = self.repository.get(ledger.uuid)
        assert updated is not None
        self.assertEqual(updated.name, "Household")
        self.assertEqual(updated.path, ledger.path)

    def test_update_icon_and_color_changes_only_appearance(self) -> None:
        """A ledger appearance can change without changing its path or identity."""
        ledger = self.create_ledger("ledger.sqlite")

        self.repository.update_icon(ledger.uuid, "WalletCards")
        self.repository.update_color_code(ledger.uuid, b"\xff\x80\x00")

        updated = self.repository.get(ledger.uuid)
        assert updated is not None
        self.assertEqual(updated.icon, "WalletCards")
        self.assertEqual(updated.color_code, b"\xff\x80\x00")
        self.assertEqual(updated.path, ledger.path)

    def test_list_all_returns_every_ledger_without_promising_order(self) -> None:
        """list_all returns the complete collection; ordering is unspecified."""
        self.create_ledger("first.sqlite")
        self.create_ledger("second.sqlite")

        ledgers = self.repository.list_all()

        self.assertCountEqual(
            [ledger.path for ledger in ledgers],
            ["first.sqlite", "second.sqlite"],
        )

    def test_delete_ledger_cascades_grants_without_deleting_user_sessions(self) -> None:
        grant_repository = SqliteLedgerGrantRepository(self.connection)
        session_repository = SqliteAuthSessionRepository(self.connection)
        invitation_repository = SqliteUserInvitationRepository(self.connection)
        user_repository = SqliteUserRepository(self.connection)
        ledger = self.create_ledger("ledger.sqlite")
        invitation = invitation_repository.create(b"i" * 32, 10, 10 + DEFAULT_EXPIRATION_TIMEOUT_SECONDS)
        user = user_repository.create("Alice", "$argon2id$test", 15)
        grant = grant_repository.create(user.uuid, ledger.uuid, "OWNER", 16)
        session = session_repository.create(user.uuid, b"s" * 32, 17, 17 + DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, DEFAULT_INACTIVITY_TIMEOUT_SECONDS)

        self.repository.delete(ledger.uuid)

        self.assertIsNone(grant_repository.get(grant.uuid))
        self.assertEqual(invitation_repository.get(invitation.uuid), invitation)
        self.assertEqual(user_repository.get(user.uuid), user)
        self.assertEqual(session_repository.get(session.uuid), session)

    def test_repository_does_not_commit_its_own_changes(self) -> None:
        """Transaction ownership remains with the unit of work."""
        self.create_ledger("ledger.sqlite")

        self.connection.rollback()

        self.assertIsNone(self.repository.get_by_path("ledger.sqlite"))

    def test_database_rejects_duplicate_paths(self) -> None:
        """The schema's unique path constraint is visible through the repository."""
        self.create_ledger("ledger.sqlite")

        with self.assertRaises(sqlite3.IntegrityError):
            self.create_ledger("ledger.sqlite")


if __name__ == "__main__":
    unittest.main()
