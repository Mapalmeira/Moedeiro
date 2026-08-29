"""Integration tests for the registry SQLite authentication session repository."""

import sqlite3
from uuid import uuid4

from tests.integration.registry_repository_test_case import RegistryRepositoryTestCase


class SqliteAuthSessionRepositoryTest(RegistryRepositoryTestCase):
    def test_create_returns_a_session_readable_by_uuid_and_token_hash(self) -> None:
        """Only the cookie token digest is persisted for later lookup."""
        grant = self.create_grant()

        session = self.session_repository.create(grant.uuid, b"t" * 32, 40)

        self.assertEqual(self.session_repository.get(session.uuid), session)
        self.assertEqual(self.session_repository.get_by_token_hash(b"t" * 32), session)
        self.assertEqual(session.inactivity_timeout_seconds, 1800)
        self.assertEqual(session.absolute_timeout_seconds, 43200)

    def test_get_returns_none_for_unknown_identity_and_token(self) -> None:
        """Unknown session identifiers and token digests are represented by None."""
        self.assertIsNone(self.session_repository.get(uuid4()))
        self.assertIsNone(self.session_repository.get_by_token_hash(b"x" * 32))

    def test_update_last_activity_records_successful_cookie_use(self) -> None:
        """Session activity can be tracked without replacing the token."""
        grant = self.create_grant()
        session = self.session_repository.create(grant.uuid, b"t" * 32, 40)

        self.session_repository.update_last_activity(session.uuid, 50)

        updated = self.session_repository.get(session.uuid)
        assert updated is not None
        self.assertEqual(updated.last_activity_at, 50)
        self.assertEqual(updated.token_hash, session.token_hash)

    def test_update_last_activity_ignores_inactive_absolutely_expired_and_revoked_sessions(self) -> None:
        """Activity is recorded only while both session timeouts remain valid."""
        grant = self.create_grant()
        inactive = self.session_repository.create(grant.uuid, b"i" * 32, 40, 10, 100)
        absolute = self.session_repository.create(grant.uuid, b"a" * 32, 40, 40, 50)
        revoked = self.session_repository.create(grant.uuid, b"r" * 32, 40)
        self.session_repository.update_last_activity(absolute.uuid, 70)
        self.session_repository.revoke(revoked.uuid, 45)

        self.session_repository.update_last_activity(inactive.uuid, 50)
        self.session_repository.update_last_activity(absolute.uuid, 90)
        self.session_repository.update_last_activity(revoked.uuid, 50)

        stored_inactive = self.session_repository.get(inactive.uuid)
        stored_absolute = self.session_repository.get(absolute.uuid)
        stored_revoked = self.session_repository.get(revoked.uuid)
        assert stored_inactive is not None
        assert stored_absolute is not None
        assert stored_revoked is not None
        self.assertIsNone(stored_inactive.last_activity_at)
        self.assertEqual(stored_absolute.last_activity_at, 70)
        self.assertIsNone(stored_revoked.last_activity_at)

    def test_revoke_preserves_the_first_timestamp(self) -> None:
        """Repeated revocation does not rewrite the original audit timestamp."""
        grant = self.create_grant()
        session = self.session_repository.create(grant.uuid, b"t" * 32, 40)

        self.session_repository.revoke(session.uuid, 50)
        self.session_repository.revoke(session.uuid, 60)

        revoked = self.session_repository.get(session.uuid)
        assert revoked is not None
        self.assertEqual(revoked.revoked_at, 50)

    def test_revoke_by_grant_revokes_only_its_active_sessions(self) -> None:
        """Grant revocation can invalidate every cookie issued through it."""
        grant = self.create_grant()
        other_grant = self.create_grant()
        first = self.session_repository.create(grant.uuid, b"a" * 32, 40)
        second = self.session_repository.create(grant.uuid, b"b" * 32, 40)
        other = self.session_repository.create(other_grant.uuid, b"c" * 32, 40)

        self.session_repository.revoke(first.uuid, 45)
        self.session_repository.revoke_by_grant(grant.uuid, 50)

        sessions = self.session_repository.list_by_grant(grant.uuid)
        self.assertCountEqual([session.uuid for session in sessions], [first.uuid, second.uuid])
        revoked_first = self.session_repository.get(first.uuid)
        revoked_second = self.session_repository.get(second.uuid)
        active_other = self.session_repository.get(other.uuid)
        assert revoked_first is not None
        assert revoked_second is not None
        assert active_other is not None
        self.assertEqual(revoked_first.revoked_at, 45)
        self.assertEqual(revoked_second.revoked_at, 50)
        self.assertIsNone(active_other.revoked_at)

    def test_token_hash_is_unique(self) -> None:
        """One cookie digest cannot resolve to multiple sessions."""
        grant = self.create_grant()
        self.session_repository.create(grant.uuid, b"t" * 32, 40)

        with self.assertRaises(sqlite3.IntegrityError):
            self.session_repository.create(grant.uuid, b"t" * 32, 40)

    def test_repository_does_not_commit_its_own_changes(self) -> None:
        """Session issuance remains part of the surrounding transaction."""
        session = self.session_repository.create(self.create_grant().uuid, b"t" * 32, 40)

        self.connection.rollback()

        self.assertIsNone(self.session_repository.get(session.uuid))


if __name__ == "__main__":
    import unittest

    unittest.main()
