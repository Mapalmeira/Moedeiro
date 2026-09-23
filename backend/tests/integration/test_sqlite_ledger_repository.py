"""Integration tests for the registry SQLite ledger repository."""

import unittest
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

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

    def create_ledger(self, path: str, last_accessed_at: int = 10):
        return self.repository.create(uuid4(), "Main ledger", path, "lucide:BookOpen", b"\x80\x80\x80", last_accessed_at)

    def tearDown(self) -> None:
        self.connection.close()
        self.temporary_directory.cleanup()

    def test_create_can_be_read_by_uuid_and_path(self) -> None:
        """create persists the supplied identity and path."""
        ledger = self.create_ledger("ledger.sqlite")

        self.assertEqual(self.repository.get(ledger.uuid), ledger)
        self.assertEqual(self.repository.get_by_path("ledger.sqlite"), ledger)

    def test_list_owned_by_user_returns_only_active_owner_ledgers(self) -> None:
        grant_repository = SqliteLedgerGrantRepository(self.connection)
        user_repository = SqliteUserRepository(self.connection)
        first = self.create_ledger("first.sqlite")
        second = self.create_ledger("second.sqlite")
        other = self.create_ledger("other.sqlite")
        first_user = user_repository.create("Alice", "$argon2id$test", 10)
        second_user = user_repository.create("Bob", "$argon2id$test", 10)
        first_grant = grant_repository.create(first_user.uuid, first.uuid, "OWNER", 20)
        grant_repository.create(first_user.uuid, second.uuid, "OWNER", 20)
        grant_repository.create(second_user.uuid, other.uuid, "OWNER", 20)
        grant_repository.revoke(first_grant.uuid, 30)

        self.assertEqual(self.repository.list_owned_by_user(first_user.uuid, "name", True), [second])

    def test_list_owned_by_user_orders_by_ledger_last_access(self) -> None:
        grant_repository = SqliteLedgerGrantRepository(self.connection)
        user = SqliteUserRepository(self.connection).create("Alice", "$argon2id$test", 10)
        older = self.create_ledger("older.sqlite", 20)
        recent = self.create_ledger("recent.sqlite", 30)
        grant_repository.create(user.uuid, older.uuid, "OWNER", 20)
        grant_repository.create(user.uuid, recent.uuid, "OWNER", 20)

        ledgers = self.repository.list_owned_by_user(user.uuid, "last_accessed_at", False)

        self.assertEqual(ledgers, [recent, older])

    def test_count_owned_by_user_counts_only_active_owner_grants(self) -> None:
        grant_repository = SqliteLedgerGrantRepository(self.connection)
        user_repository = SqliteUserRepository(self.connection)
        user = user_repository.create("Alice", "$argon2id$test", 10)
        other_user = user_repository.create("Bob", "$argon2id$test", 10)
        active = self.create_ledger("active.sqlite")
        revoked = self.create_ledger("revoked.sqlite")
        other = self.create_ledger("other.sqlite")
        grant_repository.create(user.uuid, active.uuid, "OWNER", 20)
        revoked_grant = grant_repository.create(user.uuid, revoked.uuid, "OWNER", 20)
        grant_repository.create(other_user.uuid, other.uuid, "OWNER", 20)
        grant_repository.revoke(revoked_grant.uuid, 30)

        self.assertEqual(self.repository.count_owned_by_user(user.uuid), 1)
        self.assertEqual(self.repository.count_owned_by_user(other_user.uuid), 1)

    def test_delete_ledgers_owned_by_user_deletes_only_active_owned_ledgers(self) -> None:
        grant_repository = SqliteLedgerGrantRepository(self.connection)
        user_repository = SqliteUserRepository(self.connection)
        user = user_repository.create("Alice", "$argon2id$test", 10)
        other_user = user_repository.create("Bob", "$argon2id$test", 10)
        owned = self.create_ledger("owned.sqlite")
        revoked = self.create_ledger("revoked.sqlite")
        guest = self.create_ledger("guest.sqlite")
        owned_grant = grant_repository.create(user.uuid, owned.uuid, "OWNER", 20)
        revoked_grant = grant_repository.create(user.uuid, revoked.uuid, "OWNER", 20)
        grant_repository.revoke(revoked_grant.uuid, 30)
        grant_repository.create(other_user.uuid, guest.uuid, "OWNER", 20)
        guest_grant = grant_repository.create(user.uuid, guest.uuid, "GUEST", 20)

        deleted = self.repository.delete_ledgers_owned_by_user(user.uuid)

        self.assertEqual(deleted, [owned])
        self.assertIsNone(self.repository.get(owned.uuid))
        self.assertEqual(self.repository.get(revoked.uuid), revoked)
        self.assertEqual(self.repository.get(guest.uuid), guest)
        self.assertIsNone(grant_repository.get(owned_grant.uuid))
        self.assertEqual(grant_repository.get(guest_grant.uuid), guest_grant)

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

        self.repository.update_icon(ledger.uuid, "lucide:WalletCards")
        self.repository.update_color_code(ledger.uuid, b"\xff\x80\x00")

        updated = self.repository.get(ledger.uuid)
        assert updated is not None
        self.assertEqual(updated.icon, "lucide:WalletCards")
        self.assertEqual(updated.color_code, b"\xff\x80\x00")
        self.assertEqual(updated.path, ledger.path)

    def test_update_last_accessed_at_is_monotonic(self) -> None:
        ledger = self.create_ledger("ledger.sqlite", 20)

        self.repository.update_last_accessed_at(ledger.uuid, 30)
        self.repository.update_last_accessed_at(ledger.uuid, 25)

        updated = self.repository.get(ledger.uuid)
        assert updated is not None
        self.assertEqual(updated.last_accessed_at, 30)

    def test_list_all_orders_every_ledger_and_rejects_uuid_sorting(self) -> None:
        self.repository.create(uuid4(), "Bravo", "first.sqlite", "lucide:BookOpen", b"\x80\x80\x80", 10)
        self.repository.create(uuid4(), "Alpha", "second.sqlite", "lucide:BookOpen", b"\x80\x80\x80", 20)

        ledgers = self.repository.list_all("name", False)

        self.assertEqual([ledger.name for ledger in ledgers], ["Bravo", "Alpha"])
        for sort_key in ("uuid", "path"):
            with self.subTest(sort_key=sort_key):
                with self.assertRaises(ValueError):
                    self.repository.list_all(sort_key, True)

        self.assertEqual([ledger.name for ledger in self.repository.list_all("last_accessed_at", False)], ["Alpha", "Bravo"])

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
