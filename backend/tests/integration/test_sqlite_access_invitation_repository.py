"""Integration tests for the registry SQLite access invitation repository."""

import sqlite3
from uuid import uuid4

from tests.integration.registry_repository_test_case import RegistryRepositoryTestCase


class SqliteAccessInvitationRepositoryTest(RegistryRepositoryTestCase):
    def test_create_returns_an_invitation_readable_by_uuid_and_secret_hash(self) -> None:
        """create generates both the invitation identity and reserved grant identity."""
        ledger = self.create_ledger()

        invitation = self.invitation_repository.create(ledger.uuid, b"s" * 32, 10)

        self.assertNotEqual(invitation.uuid, invitation.grant_uuid)
        self.assertEqual(invitation.expiration_timeout_seconds, 3600)
        self.assertEqual(self.invitation_repository.get(invitation.uuid), invitation)
        self.assertEqual(self.invitation_repository.get_by_secret_hash(b"s" * 32), invitation)

    def test_get_returns_none_when_invitation_does_not_exist(self) -> None:
        """An unknown identity and secret hash are represented by None."""
        self.assertIsNone(self.invitation_repository.get(uuid4()))
        self.assertIsNone(self.invitation_repository.get_by_secret_hash(b"x" * 32))

    def test_consume_succeeds_only_once_while_invitation_is_active(self) -> None:
        """The conditional update makes consumption an atomic one-use operation."""
        invitation = self.create_invitation()

        self.assertTrue(self.invitation_repository.consume(invitation.uuid, 20))
        self.assertFalse(self.invitation_repository.consume(invitation.uuid, 21))
        consumed = self.invitation_repository.get(invitation.uuid)
        assert consumed is not None
        self.assertEqual(consumed.consumed_at, 20)

    def test_consume_rejects_expired_and_not_yet_active_invitation(self) -> None:
        """The supplied operation time must fall inside the configured lifetime."""
        invitation = self.create_invitation()

        self.assertFalse(self.invitation_repository.consume(invitation.uuid, 9))
        self.assertFalse(self.invitation_repository.consume(invitation.uuid, 100))

    def test_revoke_prevents_consumption_and_preserves_first_timestamp(self) -> None:
        """A revoked invitation remains revoked and cannot later be consumed."""
        invitation = self.create_invitation()

        self.invitation_repository.revoke(invitation.uuid, 30)
        self.invitation_repository.revoke(invitation.uuid, 40)

        revoked = self.invitation_repository.get(invitation.uuid)
        assert revoked is not None
        self.assertEqual(revoked.revoked_at, 30)
        self.assertFalse(self.invitation_repository.consume(invitation.uuid, 50))

    def test_list_by_ledger_excludes_other_ledgers(self) -> None:
        """The foreign-key filter returns only invitations for the selected ledger."""
        first_ledger = self.create_ledger("first.sqlite")
        second_ledger = self.create_ledger("second.sqlite")
        first = self.create_invitation(first_ledger, b"a" * 32)
        second = self.create_invitation(first_ledger, b"b" * 32)
        self.create_invitation(second_ledger, b"c" * 32)

        invitations = self.invitation_repository.list_by_ledger(first_ledger.uuid)

        self.assertCountEqual([invitation.uuid for invitation in invitations], [first.uuid, second.uuid])

    def test_create_rejects_an_unknown_ledger(self) -> None:
        """The schema prevents invitations from referring to nonexistent ledgers."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.invitation_repository.create(uuid4(), b"s" * 32, 10)

    def test_repository_does_not_commit_its_own_changes(self) -> None:
        """Transaction ownership remains with the registry unit of work."""
        ledger = self.create_ledger()
        self.connection.commit()
        self.invitation_repository.create(ledger.uuid, b"s" * 32, 10)

        self.connection.rollback()

        self.assertIsNone(self.invitation_repository.get_by_secret_hash(b"s" * 32))


if __name__ == "__main__":
    import unittest

    unittest.main()
