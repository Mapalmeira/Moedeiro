import sqlite3
from uuid import uuid4

from app.domain.registry.model.auth_session import DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, DEFAULT_INACTIVITY_TIMEOUT_SECONDS
from tests.integration.registry_repository_test_case import RegistryRepositoryTestCase


class SqliteAuthSessionRepositoryTest(RegistryRepositoryTestCase):
    def test_create_returns_a_session_readable_by_uuid_and_token_hash(self) -> None:
        user = self.create_user()

        session = self.session_repository.create(user.uuid, b"t" * 32, 40, 40 + DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, DEFAULT_INACTIVITY_TIMEOUT_SECONDS)

        self.assertEqual(session.expires_at, 40 + 12 * 60 * 60)
        self.assertEqual(session.inactivity_timeout_seconds, 30 * 60)
        self.assertEqual(self.session_repository.get(session.uuid), session)
        self.assertEqual(self.session_repository.get_by_token_hash(b"t" * 32), session)

    def test_create_requires_an_existing_user(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.session_repository.create(uuid4(), b"t" * 32, 40, 40 + DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, DEFAULT_INACTIVITY_TIMEOUT_SECONDS)

    def test_update_last_activity_records_use_only_before_timeouts(self) -> None:
        user = self.create_user()
        active = self.session_repository.create(user.uuid, b"v" * 32, 40, 40 + DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, DEFAULT_INACTIVITY_TIMEOUT_SECONDS)
        inactive = self.session_repository.create(user.uuid, b"i" * 32, 40, 40 + DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, DEFAULT_INACTIVITY_TIMEOUT_SECONDS)
        expired = self.session_repository.create(user.uuid, b"e" * 32, 40, 40 + DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, DEFAULT_INACTIVITY_TIMEOUT_SECONDS)

        self.assertTrue(self.session_repository.update_last_activity(active.uuid, 50))
        self.assertFalse(self.session_repository.update_last_activity(inactive.uuid, 40 + 1800))
        self.assertFalse(self.session_repository.update_last_activity(expired.uuid, 40 + 43200))

        stored_active = self.session_repository.get(active.uuid)
        stored_inactive = self.session_repository.get(inactive.uuid)
        stored_expired = self.session_repository.get(expired.uuid)
        assert stored_active is not None
        assert stored_inactive is not None
        assert stored_expired is not None
        self.assertEqual(stored_active.last_activity_at, 50)
        self.assertIsNone(stored_inactive.last_activity_at)
        self.assertIsNone(stored_expired.last_activity_at)

    def test_get_active_by_token_hash_applies_absolute_and_inactivity_timeouts(self) -> None:
        user = self.create_user()
        active = self.session_repository.create(user.uuid, b"a" * 32, 40, 100, 20)
        inactive = self.session_repository.create(user.uuid, b"i" * 32, 40, 100, 10)
        expired = self.session_repository.create(user.uuid, b"e" * 32, 40, 50, 20)

        self.assertEqual(self.session_repository.get_active_by_token_hash(active.token_hash, 50), active)
        self.assertIsNone(self.session_repository.get_active_by_token_hash(inactive.token_hash, 50))
        self.assertIsNone(self.session_repository.get_active_by_token_hash(expired.token_hash, 50))
        self.assertIsNone(self.session_repository.get_active_by_token_hash(b"unknown", 50))

    def test_delete_by_user_excludes_other_users_sessions(self) -> None:
        user = self.create_user()
        first = self.session_repository.create(user.uuid, b"a" * 32, 40, 40 + DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, DEFAULT_INACTIVITY_TIMEOUT_SECONDS)
        second = self.session_repository.create(user.uuid, b"b" * 32, 40, 40 + DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, DEFAULT_INACTIVITY_TIMEOUT_SECONDS)
        other = self.session_repository.create(self.create_user().uuid, b"c" * 32, 40, 40 + DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, DEFAULT_INACTIVITY_TIMEOUT_SECONDS)
        self.session_repository.delete_by_user(user.uuid)

        sessions = self.session_repository.list_by_user(user.uuid)
        self.assertEqual(sessions, [])
        self.assertIsNone(self.session_repository.get(first.uuid))
        self.assertIsNone(self.session_repository.get(second.uuid))
        stored_other = self.session_repository.get(other.uuid)
        assert stored_other is not None

    def test_delete_inactive_before_removes_expired_and_inactive_sessions(self) -> None:
        user = self.create_user()
        expired = self.session_repository.create(user.uuid, b"e" * 32, 30, 40, 100)
        inactive = self.session_repository.create(user.uuid, b"i" * 32, 30, 100, 10)
        active = self.session_repository.create(user.uuid, b"a" * 32, 30, 100, 100)

        self.assertEqual(self.session_repository.delete_inactive_before(40), 2)
        self.assertIsNone(self.session_repository.get(expired.uuid))
        self.assertIsNone(self.session_repository.get(inactive.uuid))
        self.assertIsNotNone(self.session_repository.get(active.uuid))

    def test_token_hash_is_unique(self) -> None:
        user = self.create_user()
        self.session_repository.create(user.uuid, b"t" * 32, 40, 40 + DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, DEFAULT_INACTIVITY_TIMEOUT_SECONDS)

        with self.assertRaises(sqlite3.IntegrityError):
            self.session_repository.create(user.uuid, b"t" * 32, 40, 40 + DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, DEFAULT_INACTIVITY_TIMEOUT_SECONDS)

    def test_repository_does_not_commit_its_own_changes(self) -> None:
        session = self.session_repository.create(self.create_user().uuid, b"t" * 32, 40, 40 + DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, DEFAULT_INACTIVITY_TIMEOUT_SECONDS)

        self.connection.rollback()

        self.assertIsNone(self.session_repository.get(session.uuid))
