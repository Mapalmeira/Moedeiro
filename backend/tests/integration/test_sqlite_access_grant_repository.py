"""Integration tests for the registry SQLite access grant repository."""

import sqlite3
from uuid import uuid4

from tests.integration.registry_repository_test_case import RegistryRepositoryTestCase


class SqliteAccessGrantRepositoryTest(RegistryRepositoryTestCase):
    def test_create_webcrypto_uses_the_identity_reserved_by_invitation(self) -> None:
        """The persisted grant is both authorization and WebCrypto credential."""
        invitation = self.create_invitation()

        grant = self.grant_repository.create_webcrypto(invitation.grant_uuid, invitation.ledger_uuid, "firefox", b"public-key", 20)

        self.assertEqual(grant.uuid, invitation.grant_uuid)
        self.assertEqual(grant.authentication_method, "WEBCRYPTO")
        self.assertEqual(self.grant_repository.get(grant.uuid), grant)

    def test_create_webauthn_can_be_discovered_by_credential_id(self) -> None:
        """A discoverable WebAuthn response resolves directly to its grant."""
        invitation = self.create_invitation()

        grant = self.grant_repository.create_webauthn(invitation.grant_uuid, invitation.ledger_uuid, "phone", b"public-key", b"credential-id", 3, 20)

        self.assertEqual(self.grant_repository.get_by_credential_id(b"credential-id"), grant)
        self.assertEqual(grant.authentication_method, "WEBAUTHN")
        self.assertEqual(grant.signature_counter, 3)

    def test_get_returns_none_when_grant_does_not_exist(self) -> None:
        """Unknown grant and WebAuthn identifiers are represented by None."""
        self.assertIsNone(self.grant_repository.get(uuid4()))
        self.assertIsNone(self.grant_repository.get_by_credential_id(b"unknown"))

    def test_create_requires_an_existing_ledger(self) -> None:
        """A grant can authorize only a ledger registered locally."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.grant_repository.create_webcrypto(uuid4(), uuid4(), None, b"public-key", 20)

    def test_webauthn_credential_id_is_unique(self) -> None:
        """One authenticator credential cannot resolve to multiple grants."""
        first_invitation = self.create_invitation()
        second_invitation = self.create_invitation(self.create_ledger("second.sqlite"), b"s" * 32)
        self.grant_repository.create_webauthn(first_invitation.grant_uuid, first_invitation.ledger_uuid, None, b"first-key", b"credential-id", 0, 20)

        with self.assertRaises(sqlite3.IntegrityError):
            self.grant_repository.create_webauthn(second_invitation.grant_uuid, second_invitation.ledger_uuid, None, b"second-key", b"credential-id", 0, 20)

    def test_update_webauthn_state_changes_counter(self) -> None:
        """WebAuthn authentication persists its signature counter."""
        invitation = self.create_invitation()
        grant = self.grant_repository.create_webauthn(invitation.grant_uuid, invitation.ledger_uuid, None, b"public-key", b"credential-id", 3, 20)

        self.grant_repository.update_webauthn_state(grant.uuid, 4)

        updated = self.grant_repository.get(grant.uuid)
        assert updated is not None
        self.assertEqual(updated.signature_counter, 4)

    def test_update_webauthn_state_does_not_modify_webcrypto(self) -> None:
        """Authenticator state cannot accidentally be added to WebCrypto grants."""
        grant = self.create_grant()

        self.grant_repository.update_webauthn_state(grant.uuid, 1)

        self.assertEqual(self.grant_repository.get(grant.uuid), grant)

    def test_webauthn_state_does_not_modify_revoked_grants(self) -> None:
        """A revoked grant no longer accepts authenticator state changes."""
        invitation = self.create_invitation()
        grant = self.grant_repository.create_webauthn(invitation.grant_uuid, invitation.ledger_uuid, None, b"public-key", b"credential-id", 3, 20)
        self.grant_repository.revoke(grant.uuid, 30)

        self.grant_repository.update_webauthn_state(grant.uuid, 4)

        revoked = self.grant_repository.get(grant.uuid)
        assert revoked is not None
        self.assertEqual(revoked.signature_counter, 3)

    def test_revoke_preserves_first_timestamp_and_list_filters_by_ledger(self) -> None:
        """Grants are listed by ledger and revocation remains idempotent."""
        first_ledger = self.create_ledger("first.sqlite")
        second_ledger = self.create_ledger("second.sqlite")
        first = self.create_grant(self.create_invitation(first_ledger, b"a" * 32))
        second = self.create_grant(self.create_invitation(first_ledger, b"b" * 32))
        other = self.create_grant(self.create_invitation(second_ledger, b"c" * 32))

        self.grant_repository.revoke(first.uuid, 30)
        self.grant_repository.revoke(first.uuid, 40)
        grants = self.grant_repository.list_by_ledger(first_ledger.uuid)

        self.assertCountEqual([grant.uuid for grant in grants], [first.uuid, second.uuid])
        self.assertNotIn(other.uuid, [grant.uuid for grant in grants])
        revoked = self.grant_repository.get(first.uuid)
        assert revoked is not None
        self.assertEqual(revoked.revoked_at, 30)

    def test_repository_does_not_commit_its_own_changes(self) -> None:
        """Grant registration remains atomic with invitation consumption."""
        grant = self.create_grant()

        self.connection.rollback()

        self.assertIsNone(self.grant_repository.get(grant.uuid))


if __name__ == "__main__":
    import unittest

    unittest.main()
