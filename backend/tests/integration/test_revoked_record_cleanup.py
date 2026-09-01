from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

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

    def test_removes_only_records_revoked_on_or_before_the_retention_cutoff(self) -> None:
        timestamp = 100 * SECONDS_PER_DAY
        cutoff = timestamp - 30 * SECONDS_PER_DAY
        with self.open_registry() as unit_of_work:
            user = unit_of_work.user_repository.create("Alice", "$argon2id$test", 1)
            ledger = unit_of_work.ledger_repository.create("Ledger", "ledger.sqlite", "BookOpen", b"\x80\x80\x80")
            recent_ledger = unit_of_work.ledger_repository.create("Recent Ledger", "recent-ledger.sqlite", "BookOpen", b"\x80\x80\x80")
            old_invitation = unit_of_work.user_invitation_repository.create(b"i" * 32, 1, timestamp)
            recent_invitation = unit_of_work.user_invitation_repository.create(b"j" * 32, 1, timestamp)
            old_grant = unit_of_work.ledger_grant_repository.create(user.uuid, ledger.uuid, "OWNER", 1)
            recent_grant = unit_of_work.ledger_grant_repository.create(user.uuid, recent_ledger.uuid, "OWNER", cutoff + 1)
            old_code = unit_of_work.recovery_code_repository.create(user.uuid, b"c" * 32, 1)
            recent_code = unit_of_work.recovery_code_repository.create(user.uuid, b"d" * 32, 1)
            old_session = unit_of_work.auth_session_repository.create(user.uuid, b"s" * 32, cutoff, timestamp, timestamp)
            recent_session = unit_of_work.auth_session_repository.create(user.uuid, b"t" * 32, cutoff + 1, timestamp, timestamp)
            old_remember_session = unit_of_work.remember_session_repository.create(user.uuid, b"r" * 32, 1, timestamp)
            recent_remember_session = unit_of_work.remember_session_repository.create(user.uuid, b"q" * 32, 1, timestamp)
            for repository, old_record, recent_record in (
                (unit_of_work.user_invitation_repository, old_invitation, recent_invitation),
                (unit_of_work.ledger_grant_repository, old_grant, recent_grant),
                (unit_of_work.recovery_code_repository, old_code, recent_code),
                (unit_of_work.auth_session_repository, old_session, recent_session),
                (unit_of_work.remember_session_repository, old_remember_session, recent_remember_session),
            ):
                repository.revoke(old_record.uuid, cutoff)
                repository.revoke(recent_record.uuid, cutoff + 1)
            unit_of_work.commit()

        deleted_count = remove_inactive_records(self.open_registry, timestamp, 30)

        self.assertEqual(deleted_count, 5)
        with self.open_registry() as unit_of_work:
            for repository, old_record, recent_record in (
                (unit_of_work.user_invitation_repository, old_invitation, recent_invitation),
                (unit_of_work.ledger_grant_repository, old_grant, recent_grant),
                (unit_of_work.recovery_code_repository, old_code, recent_code),
                (unit_of_work.auth_session_repository, old_session, recent_session),
                (unit_of_work.remember_session_repository, old_remember_session, recent_remember_session),
            ):
                with self.subTest(repository=type(repository).__name__):
                    self.assertIsNone(repository.get(old_record.uuid))
                    self.assertIsNotNone(repository.get(recent_record.uuid))

    def test_rejects_a_nonpositive_retention_period(self) -> None:
        with self.assertRaises(ValueError):
            remove_inactive_records(self.open_registry, 100, 0)

    def test_removes_expired_consumed_used_and_unconfirmed_records(self) -> None:
        timestamp = 100 * SECONDS_PER_DAY
        cutoff = timestamp - 30 * SECONDS_PER_DAY
        with self.open_registry() as unit_of_work:
            user = unit_of_work.user_repository.create("Bob", "$argon2id$test", 1)
            confirmed_user = unit_of_work.user_repository.create("Carol", "$argon2id$test", 1)
            expired_invitation = unit_of_work.user_invitation_repository.create(b"e" * 32, 1, cutoff)
            consumed_invitation = unit_of_work.user_invitation_repository.create(b"c" * 32, 1, timestamp)
            unit_of_work.user_invitation_repository.consume(consumed_invitation.uuid, cutoff)
            used_code = unit_of_work.recovery_code_repository.create(user.uuid, b"u" * 32, 1)
            unit_of_work.recovery_code_repository.consume(used_code.uuid, cutoff)
            expired_session = unit_of_work.auth_session_repository.create(user.uuid, b"s" * 32, 1, cutoff, 1)
            inactive_session = unit_of_work.auth_session_repository.create(user.uuid, b"i" * 32, 1, timestamp, 1)
            expired_remember_session = unit_of_work.remember_session_repository.create(user.uuid, b"r" * 32, 1, cutoff)
            pending_method = unit_of_work.mfa_method_repository.create(user.uuid, "TOTP", b"pending", cutoff)
            confirmed_method = unit_of_work.mfa_method_repository.create(confirmed_user.uuid, "TOTP", b"confirmed", 1, 2)
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


if __name__ == "__main__":
    unittest.main()
