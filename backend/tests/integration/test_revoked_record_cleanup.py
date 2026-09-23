import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from app.application.registry.use_cases.cleanup import SECONDS_PER_DAY, remove_inactive_records
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.registry.unit_of_work import SqliteRegistryUnitOfWork


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"


class InactiveRecordCleanupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.database = SqliteDatabase.initialize(Path(self.temporary_directory.name) / "registry.sqlite", SCHEMA_PATH)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def open_registry(self) -> SqliteRegistryUnitOfWork:
        return SqliteRegistryUnitOfWork(self.database)

    def test_pending_cleanup_counts_retention_from_expiration(self) -> None:
        timestamp = 100 * SECONDS_PER_DAY
        cutoff = timestamp - 30 * SECONDS_PER_DAY
        with self.open_registry() as unit_of_work:
            old_user = unit_of_work.user_repository.create("Old", "hash", 1)
            recent_user = unit_of_work.user_repository.create("Recent", "hash", 1)
            old = unit_of_work.mfa_method_repository.create(old_user.uuid, "TOTP", b"old", 1, cutoff)
            recent = unit_of_work.mfa_method_repository.create(recent_user.uuid, "TOTP", b"recent", 1, cutoff + 1)
            unit_of_work.commit()
        self.assertEqual(remove_inactive_records(self.open_registry, timestamp, 30), 1)
        with self.open_registry() as unit_of_work:
            self.assertIsNone(unit_of_work.mfa_method_repository.get(old.uuid))
            self.assertIsNotNone(unit_of_work.mfa_method_repository.get(recent.uuid))

    def test_removes_only_grants_revoked_on_or_before_the_retention_cutoff(self) -> None:
        timestamp = 100 * SECONDS_PER_DAY
        cutoff = timestamp - 30 * SECONDS_PER_DAY
        with self.open_registry() as unit_of_work:
            user = unit_of_work.user_repository.create("Alice", "$argon2id$test", 1)
            ledger = unit_of_work.ledger_repository.create(uuid4(), "Ledger", "ledger.sqlite", "lucide:BookOpen", b"\x80\x80\x80", 1)
            recent_ledger = unit_of_work.ledger_repository.create(uuid4(), "Recent Ledger", "recent-ledger.sqlite", "lucide:BookOpen", b"\x80\x80\x80", 1)
            old_grant = unit_of_work.ledger_grant_repository.create(user.uuid, ledger.uuid, "OWNER", 1)
            recent_grant = unit_of_work.ledger_grant_repository.create(user.uuid, recent_ledger.uuid, "OWNER", cutoff + 1)
            unit_of_work.ledger_grant_repository.revoke(old_grant.uuid, cutoff)
            unit_of_work.ledger_grant_repository.revoke(recent_grant.uuid, cutoff + 1)
            unit_of_work.commit()

        deleted_count = remove_inactive_records(self.open_registry, timestamp, 30)

        self.assertEqual(deleted_count, 1)
        with self.open_registry() as unit_of_work:
            self.assertIsNone(unit_of_work.ledger_grant_repository.get(old_grant.uuid))
            self.assertIsNotNone(unit_of_work.ledger_grant_repository.get(recent_grant.uuid))


    def test_removing_revoked_guest_grant_removes_orphaned_external_access(self) -> None:
        timestamp = 100 * SECONDS_PER_DAY
        cutoff = timestamp - 30 * SECONDS_PER_DAY
        with self.open_registry() as unit_of_work:
            user = unit_of_work.user_repository.create("Alice", "$argon2id$test", 1)
            ledger = unit_of_work.ledger_repository.create(uuid4(), "Ledger", "ledger.sqlite", "lucide:BookOpen", b"\x80\x80\x80", 1)
            access = unit_of_work.external_access_repository.create("Sync plugin", b"t" * 32)
            grant = unit_of_work.ledger_grant_repository.create(access.uuid, ledger.uuid, "GUEST", 1)
            unit_of_work.ledger_grant_repository.revoke(grant.uuid, cutoff)
            unit_of_work.commit()

        self.assertEqual(remove_inactive_records(self.open_registry, timestamp, 30), 1)

        with self.open_registry() as unit_of_work:
            self.assertIsNone(unit_of_work.ledger_grant_repository.get(grant.uuid))
            self.assertIsNone(unit_of_work.external_access_repository.get(access.uuid))

    def test_rejects_a_negative_retention_period(self) -> None:
        with self.assertRaises(ValueError):
            remove_inactive_records(self.open_registry, 100, -1)

    def test_zero_day_retention_removes_all_inactive_records_now(self) -> None:
        with self.open_registry() as unit_of_work:
            user = unit_of_work.user_repository.create("Alice", "$argon2id$test", 1)
            ledger = unit_of_work.ledger_repository.create(uuid4(), "Ledger", "ledger.sqlite", "lucide:BookOpen", b"\x80\x80\x80", 1)
            grant = unit_of_work.ledger_grant_repository.create(user.uuid, ledger.uuid, "OWNER", 1)
            unit_of_work.ledger_grant_repository.revoke(grant.uuid, 100)
            unit_of_work.commit()

        self.assertEqual(remove_inactive_records(self.open_registry, 100, 0), 1)
        with self.open_registry() as unit_of_work:
            self.assertIsNone(unit_of_work.ledger_grant_repository.get(grant.uuid))

    def test_removes_expired_consumed_used_and_unconfirmed_records(self) -> None:
        timestamp = 100 * SECONDS_PER_DAY
        cutoff = timestamp - 30 * SECONDS_PER_DAY
        with self.open_registry() as unit_of_work:
            user = unit_of_work.user_repository.create("Bob", "$argon2id$test", 1)
            confirmed_user = unit_of_work.user_repository.create("Carol", "$argon2id$test", 1)
            expired_invitation = unit_of_work.user_invitation_repository.create(b"e" * 32, 1, cutoff)
            consumed_invitation = unit_of_work.user_invitation_repository.create(b"c" * 32, 1, timestamp)
            unit_of_work.user_invitation_repository.consume(consumed_invitation.uuid, cutoff)
            used_code = unit_of_work.recovery_code_repository.create(user.uuid, b"u" * 32, 1, timestamp)
            unit_of_work.recovery_code_repository.consume(used_code.uuid, cutoff)
            expired_session = unit_of_work.auth_session_repository.create(user.uuid, b"s" * 32, 1, cutoff, 1)
            inactive_session = unit_of_work.auth_session_repository.create(user.uuid, b"i" * 32, 1, timestamp, 1)
            expired_remember_session = unit_of_work.remember_session_repository.create(user.uuid, b"r" * 32, 1, cutoff)
            pending_method = unit_of_work.mfa_method_repository.create(user.uuid, "TOTP", b"pending", 1, cutoff)
            confirmed_method = unit_of_work.mfa_method_repository.create(confirmed_user.uuid, "TOTP", b"confirmed", 1, 601, 2)
            unit_of_work.commit()

        deleted_count = remove_inactive_records(self.open_registry, timestamp, 30)

        self.assertEqual(deleted_count, 7)
        with self.open_registry() as unit_of_work:
            self.assertIsNone(unit_of_work.user_invitation_repository.get(expired_invitation.uuid))
            self.assertIsNone(unit_of_work.user_invitation_repository.get(consumed_invitation.uuid))
            self.assertIsNone(unit_of_work.recovery_code_repository.get(used_code.uuid))
            self.assertIsNone(unit_of_work.auth_session_repository.get(expired_session.uuid))
            self.assertIsNone(unit_of_work.auth_session_repository.get(inactive_session.uuid))
            self.assertIsNone(unit_of_work.remember_session_repository.get(expired_remember_session.uuid))
            self.assertIsNone(unit_of_work.mfa_method_repository.get(pending_method.uuid))
            self.assertIsNotNone(unit_of_work.mfa_method_repository.get(confirmed_method.uuid))
