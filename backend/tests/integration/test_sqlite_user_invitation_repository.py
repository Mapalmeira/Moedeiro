import sqlite3
from uuid import uuid4

from app.domain.registry.model.user_invitation import DEFAULT_EXPIRATION_TIMEOUT_SECONDS
from tests.integration.registry_repository_test_case import RegistryRepositoryTestCase


class SqliteUserInvitationRepositoryTest(RegistryRepositoryTestCase):
    def test_create_returns_an_invitation_readable_by_uuid_and_secret_hash(self) -> None:
        invitation = self.invitation_repository.create(b"s" * 32, 10, 10 + DEFAULT_EXPIRATION_TIMEOUT_SECONDS)

        self.assertEqual(invitation.expires_at, 3610)
        self.assertEqual(self.invitation_repository.get(invitation.uuid), invitation)
        self.assertEqual(self.invitation_repository.get_by_secret_hash(b"s" * 32), invitation)

    def test_get_returns_none_when_invitation_does_not_exist(self) -> None:
        self.assertIsNone(self.invitation_repository.get(uuid4()))
        self.assertIsNone(self.invitation_repository.get_by_secret_hash(b"x" * 32))

    def test_consume_succeeds_only_once_while_invitation_is_active(self) -> None:
        invitation = self.create_invitation()

        self.assertTrue(self.invitation_repository.consume(invitation.uuid, 20))
        self.assertFalse(self.invitation_repository.consume(invitation.uuid, 21))
        consumed = self.invitation_repository.get(invitation.uuid)
        assert consumed is not None
        self.assertEqual(consumed.consumed_at, 20)

    def test_consume_rejects_time_outside_invitation_lifetime(self) -> None:
        invitation = self.create_invitation()

        self.assertFalse(self.invitation_repository.consume(invitation.uuid, 9))
        self.assertFalse(self.invitation_repository.consume(invitation.uuid, 100))

    def test_revoke_prevents_consumption_and_preserves_first_timestamp(self) -> None:
        invitation = self.create_invitation()

        self.invitation_repository.revoke(invitation.uuid, 30)
        self.invitation_repository.revoke(invitation.uuid, 40)

        revoked = self.invitation_repository.get(invitation.uuid)
        assert revoked is not None
        self.assertEqual(revoked.revoked_at, 30)
        self.assertFalse(self.invitation_repository.consume(invitation.uuid, 50))

    def test_list_all_returns_consumed_revoked_and_active_invitations(self) -> None:
        consumed = self.create_invitation(b"a" * 32)
        revoked = self.create_invitation(b"b" * 32)
        active = self.create_invitation(b"c" * 32)
        self.invitation_repository.consume(consumed.uuid, 20)
        self.invitation_repository.revoke(revoked.uuid, 20)

        invitations = self.invitation_repository.list_all()

        self.assertCountEqual([invitation.uuid for invitation in invitations], [consumed.uuid, revoked.uuid, active.uuid])

    def test_secret_hash_is_unique(self) -> None:
        self.create_invitation(b"s" * 32)

        with self.assertRaises(sqlite3.IntegrityError):
            self.create_invitation(b"s" * 32)

    def test_repository_does_not_commit_its_own_changes(self) -> None:
        invitation = self.create_invitation()

        self.connection.rollback()

        self.assertIsNone(self.invitation_repository.get(invitation.uuid))


if __name__ == "__main__":
    import unittest

    unittest.main()
