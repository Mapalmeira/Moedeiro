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

    def test_delete_removes_only_an_unused_invitation(self) -> None:
        invitation = self.create_invitation()

        self.assertTrue(self.invitation_repository.delete(invitation.uuid))
        self.assertFalse(self.invitation_repository.delete(invitation.uuid))
        self.assertIsNone(self.invitation_repository.get(invitation.uuid))

        consumed = self.create_invitation(b"c" * 32)
        self.assertTrue(self.invitation_repository.consume(consumed.uuid, 20))
        self.assertFalse(self.invitation_repository.delete(consumed.uuid))
        self.assertIsNotNone(self.invitation_repository.get(consumed.uuid))

    def test_list_all_orders_consumed_and_active_invitations(self) -> None:
        consumed = self.invitation_repository.create(b"a" * 32, 10, 100)
        active = self.invitation_repository.create(b"c" * 32, 20, 100)
        self.invitation_repository.consume(consumed.uuid, 20)

        invitations = self.invitation_repository.list_all("created_at", False)

        self.assertEqual(invitations, [active, consumed.model_copy(update={"consumed_at": 20})])
        with self.assertRaises(ValueError):
            self.invitation_repository.list_all("uuid", True)

    def test_delete_inactive_before_removes_expired_and_consumed_invitations(self) -> None:
        expired = self.invitation_repository.create(b"e" * 32, 10, 40)
        consumed = self.invitation_repository.create(b"c" * 32, 10, 100)
        active = self.invitation_repository.create(b"a" * 32, 10, 100)
        self.assertTrue(self.invitation_repository.consume(consumed.uuid, 40))

        self.assertEqual(self.invitation_repository.delete_inactive_before(40), 2)
        self.assertIsNone(self.invitation_repository.get(expired.uuid))
        self.assertIsNone(self.invitation_repository.get(consumed.uuid))
        self.assertIsNotNone(self.invitation_repository.get(active.uuid))

    def test_secret_hash_is_unique(self) -> None:
        self.create_invitation(b"s" * 32)

        with self.assertRaises(sqlite3.IntegrityError):
            self.create_invitation(b"s" * 32)

    def test_repository_does_not_commit_its_own_changes(self) -> None:
        invitation = self.create_invitation()

        self.connection.rollback()

        self.assertIsNone(self.invitation_repository.get(invitation.uuid))
