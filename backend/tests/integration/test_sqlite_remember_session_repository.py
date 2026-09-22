import sqlite3
from uuid import uuid4

from app.domain.registry.model.remember_session import DEFAULT_EXPIRATION_TIMEOUT_SECONDS
from tests.integration.registry_repository_test_case import RegistryRepositoryTestCase


class SqliteRememberSessionRepositoryTest(RegistryRepositoryTestCase):
    def test_create_can_be_read_by_uuid_and_token_hash(self) -> None:
        user = self.create_user()

        session = self.remember_session_repository.create(user.uuid, b"t" * 32, 30, 30 + DEFAULT_EXPIRATION_TIMEOUT_SECONDS)

        self.assertEqual(session.expires_at, 30 + 30 * 24 * 60 * 60)
        self.assertEqual(self.remember_session_repository.get(session.uuid), session)
        self.assertEqual(self.remember_session_repository.get_by_token_hash(b"t" * 32), session)

    def test_create_requires_an_existing_user_and_unique_token_hash(self) -> None:
        user = self.create_user()
        self.remember_session_repository.create(user.uuid, b"t" * 32, 30, 30 + DEFAULT_EXPIRATION_TIMEOUT_SECONDS)

        with self.assertRaises(sqlite3.IntegrityError):
            self.remember_session_repository.create(user.uuid, b"t" * 32, 31, 31 + DEFAULT_EXPIRATION_TIMEOUT_SECONDS)
        with self.assertRaises(sqlite3.IntegrityError):
            self.remember_session_repository.create(uuid4(), b"u" * 32, 30, 30 + DEFAULT_EXPIRATION_TIMEOUT_SECONDS)

    def test_rotate_replaces_token_and_records_use_while_active(self) -> None:
        session = self.remember_session_repository.create(self.create_user().uuid, b"o" * 32, 30, 130)

        self.assertTrue(self.remember_session_repository.rotate(session.uuid, b"o" * 32, b"n" * 32, 40))

        self.assertIsNone(self.remember_session_repository.get_by_token_hash(b"o" * 32))
        rotated = self.remember_session_repository.get_by_token_hash(b"n" * 32)
        assert rotated is not None
        self.assertEqual(rotated.last_used_at, 40)

    def test_rotate_rejects_a_stale_token_hash(self) -> None:
        session = self.remember_session_repository.create(self.create_user().uuid, b"o" * 32, 30, 130)

        self.assertFalse(self.remember_session_repository.rotate(session.uuid, b"wrong", b"n" * 32, 40))

        self.assertEqual(self.remember_session_repository.get_by_token_hash(b"o" * 32), session)
        self.assertIsNone(self.remember_session_repository.get_by_token_hash(b"n" * 32))

    def test_rotate_rejects_an_expired_session(self) -> None:
        expired = self.remember_session_repository.create(self.create_user().uuid, b"e" * 32, 30, 40)

        self.assertFalse(self.remember_session_repository.rotate(expired.uuid, b"e" * 32, b"x" * 32, 40))

    def test_delete_by_user_excludes_other_users_sessions(self) -> None:
        user = self.create_user()
        first = self.remember_session_repository.create(user.uuid, b"a" * 32, 30, 30 + DEFAULT_EXPIRATION_TIMEOUT_SECONDS)
        second = self.remember_session_repository.create(user.uuid, b"b" * 32, 30, 30 + DEFAULT_EXPIRATION_TIMEOUT_SECONDS)
        other = self.remember_session_repository.create(self.create_user().uuid, b"c" * 32, 30, 30 + DEFAULT_EXPIRATION_TIMEOUT_SECONDS)
        self.remember_session_repository.delete_by_user(user.uuid)

        sessions = self.remember_session_repository.list_by_user(user.uuid)
        self.assertEqual(sessions, [])
        self.assertIsNone(self.remember_session_repository.get(first.uuid))
        self.assertIsNone(self.remember_session_repository.get(second.uuid))
        stored_other = self.remember_session_repository.get(other.uuid)
        assert stored_other is not None

    def test_delete_inactive_before_removes_expired_sessions(self) -> None:
        user = self.create_user()
        expired = self.remember_session_repository.create(user.uuid, b"e" * 32, 30, 40)
        active = self.remember_session_repository.create(user.uuid, b"a" * 32, 30, 100)

        self.assertEqual(self.remember_session_repository.delete_inactive_before(40), 1)
        self.assertIsNone(self.remember_session_repository.get(expired.uuid))
        self.assertIsNotNone(self.remember_session_repository.get(active.uuid))
