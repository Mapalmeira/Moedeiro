import sqlite3
from uuid import uuid4

from tests.integration.registry_repository_test_case import RegistryRepositoryTestCase


class SqliteAuthSessionRepositoryTest(RegistryRepositoryTestCase):
    def test_create_returns_a_session_readable_by_uuid_and_token_hash(self) -> None:
        user = self.create_user()

        session = self.session_repository.create(user.uuid, b"t" * 32, 40)

        self.assertEqual(self.session_repository.get(session.uuid), session)
        self.assertEqual(self.session_repository.get_by_token_hash(b"t" * 32), session)

    def test_create_requires_an_existing_user(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.session_repository.create(uuid4(), b"t" * 32, 40)

    def test_update_last_activity_records_use_only_while_session_is_active(self) -> None:
        user = self.create_user()
        active = self.session_repository.create(user.uuid, b"v" * 32, 40)
        inactive = self.session_repository.create(user.uuid, b"i" * 32, 40)
        expired = self.session_repository.create(user.uuid, b"e" * 32, 40)
        revoked = self.session_repository.create(user.uuid, b"r" * 32, 40)
        self.session_repository.revoke(revoked.uuid, 45)

        self.session_repository.update_last_activity(active.uuid, 50)
        self.session_repository.update_last_activity(inactive.uuid, 40 + 1800)
        self.session_repository.update_last_activity(expired.uuid, 40 + 43200)
        self.session_repository.update_last_activity(revoked.uuid, 50)

        stored_active = self.session_repository.get(active.uuid)
        stored_inactive = self.session_repository.get(inactive.uuid)
        stored_expired = self.session_repository.get(expired.uuid)
        stored_revoked = self.session_repository.get(revoked.uuid)
        assert stored_active is not None
        assert stored_inactive is not None
        assert stored_expired is not None
        assert stored_revoked is not None
        self.assertEqual(stored_active.last_activity_at, 50)
        self.assertIsNone(stored_inactive.last_activity_at)
        self.assertIsNone(stored_expired.last_activity_at)
        self.assertIsNone(stored_revoked.last_activity_at)

    def test_revoke_by_user_preserves_existing_revocation_and_excludes_other_user(self) -> None:
        user = self.create_user()
        first = self.session_repository.create(user.uuid, b"a" * 32, 40)
        second = self.session_repository.create(user.uuid, b"b" * 32, 40)
        other = self.session_repository.create(self.create_user().uuid, b"c" * 32, 40)
        self.session_repository.revoke(first.uuid, 45)

        self.session_repository.revoke_by_user(user.uuid, 50)

        sessions = self.session_repository.list_by_user(user.uuid)
        self.assertCountEqual([session.uuid for session in sessions], [first.uuid, second.uuid])
        stored_first = self.session_repository.get(first.uuid)
        stored_second = self.session_repository.get(second.uuid)
        stored_other = self.session_repository.get(other.uuid)
        assert stored_first is not None
        assert stored_second is not None
        assert stored_other is not None
        self.assertEqual(stored_first.revoked_at, 45)
        self.assertEqual(stored_second.revoked_at, 50)
        self.assertIsNone(stored_other.revoked_at)

    def test_token_hash_is_unique(self) -> None:
        user = self.create_user()
        self.session_repository.create(user.uuid, b"t" * 32, 40)

        with self.assertRaises(sqlite3.IntegrityError):
            self.session_repository.create(user.uuid, b"t" * 32, 40)

    def test_repository_does_not_commit_its_own_changes(self) -> None:
        session = self.session_repository.create(self.create_user().uuid, b"t" * 32, 40)

        self.connection.rollback()

        self.assertIsNone(self.session_repository.get(session.uuid))


if __name__ == "__main__":
    import unittest

    unittest.main()
