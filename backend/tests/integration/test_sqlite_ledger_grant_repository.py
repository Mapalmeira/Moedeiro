import sqlite3
from uuid import uuid4

from tests.integration.registry_repository_test_case import RegistryRepositoryTestCase


class SqliteLedgerGrantRepositoryTest(RegistryRepositoryTestCase):
    def test_create_returns_an_owner_grant_readable_by_uuid_and_active_relation(self) -> None:
        user = self.create_user()
        ledger = self.create_ledger()

        grant = self.grant_repository.create(user.uuid, ledger.uuid, "OWNER", 30)

        self.assertEqual(self.grant_repository.get(grant.uuid), grant)
        self.assertEqual(self.grant_repository.get_active_owner(user.uuid, ledger.uuid), grant)
        self.assertEqual(self.grant_repository.get_active_owner_by_ledger(ledger.uuid), grant)
        self.assertEqual(grant.grantee_uuid, user.uuid)

    def test_create_requires_existing_grantee_and_ledger(self) -> None:
        user = self.create_user()
        ledger = self.create_ledger()
        invalid_relations = ((uuid4(), ledger.uuid), (user.uuid, uuid4()))

        for grantee_uuid, ledger_uuid in invalid_relations:
            with self.subTest(grantee_uuid=grantee_uuid, ledger_uuid=ledger_uuid):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.grant_repository.create(grantee_uuid, ledger_uuid, "OWNER", 30)

    def test_multiple_active_guest_grants_can_exist_for_one_ledger(self) -> None:
        user = self.create_user()
        ledger = self.create_ledger()
        first = self.create_grant(user, ledger, "GUEST", "First", b"a" * 32)
        second = self.create_grant(user, ledger, "GUEST", "Second", b"b" * 32)

        self.assertCountEqual(self.grant_repository.list_by_ledger(ledger.uuid), [first, second])

    def test_only_one_active_owner_exists_for_each_ledger(self) -> None:
        first_user = self.create_user()
        second_user = self.create_user()
        ledger = self.create_ledger()
        self.grant_repository.create(first_user.uuid, ledger.uuid, "OWNER", 30)

        with self.assertRaises(sqlite3.IntegrityError):
            self.grant_repository.create(second_user.uuid, ledger.uuid, "OWNER", 31)

    def test_revoked_owner_can_be_replaced(self) -> None:
        user = self.create_user()
        ledger = self.create_ledger()
        original = self.grant_repository.create(user.uuid, ledger.uuid, "OWNER", 30)
        self.grant_repository.revoke(original.uuid, 40)

        replacement = self.grant_repository.create(user.uuid, ledger.uuid, "OWNER", 50)

        self.assertEqual(self.grant_repository.get_active_owner(user.uuid, ledger.uuid), replacement)

    def test_revoke_is_idempotent_and_removes_active_relation(self) -> None:
        grant = self.create_grant()

        self.grant_repository.revoke(grant.uuid, 40)
        self.grant_repository.revoke(grant.uuid, 50)

        revoked = self.grant_repository.get(grant.uuid)
        assert revoked is not None
        self.assertEqual(revoked.revoked_at, 40)
        self.assertIsNone(self.grant_repository.get_active_owner(grant.grantee_uuid, grant.ledger_uuid))

    def test_list_methods_filter_by_grantee_and_ledger(self) -> None:
        first_user = self.create_user()
        second_user = self.create_user()
        first_ledger = self.create_ledger()
        second_ledger = self.create_ledger()
        owner = self.create_grant(first_user, first_ledger)
        guest = self.create_grant(first_user, first_ledger, "GUEST", "Plugin", b"p" * 32)
        second = self.create_grant(first_user, second_ledger)
        third_ledger = self.create_ledger()
        third = self.create_grant(second_user, third_ledger)

        self.assertCountEqual(self.grant_repository.list_by_grantee(first_user.uuid), [owner, second])
        self.assertEqual(self.grant_repository.list_by_grantee(guest.grantee_uuid), [guest])
        self.assertCountEqual(self.grant_repository.list_by_ledger(first_ledger.uuid), [owner, guest])
        self.assertEqual(self.grant_repository.list_by_grantee(second_user.uuid), [third])

    def test_revoke_active_guests_by_ledger_and_role_only_revokes_matching_active_grants(self) -> None:
        user = self.create_user()
        other_user = self.create_user()
        ledger = self.create_ledger()
        other_ledger = self.create_ledger()
        owner = self.create_grant(user, ledger)
        first = self.create_grant(user, ledger, "GUEST", "First", b"a" * 32)
        second = self.create_grant(other_user, ledger, "GUEST", "Second", b"b" * 32)
        already_revoked = self.create_grant(user, ledger, "GUEST", "Revoked", b"c" * 32)
        other_ledger_grant = self.create_grant(user, other_ledger, "GUEST", "Other ledger", b"d" * 32)
        self.grant_repository.revoke(already_revoked.uuid, 35)

        self.grant_repository.revoke_active_guests_by_ledger_and_role(ledger.uuid, "GUEST", 40)

        self.assertEqual(self.grant_repository.get(first.uuid).revoked_at, 40)
        self.assertEqual(self.grant_repository.get(second.uuid).revoked_at, 40)
        self.assertEqual(self.grant_repository.get(already_revoked.uuid).revoked_at, 35)
        self.assertIsNone(self.grant_repository.get(owner.uuid).revoked_at)
        self.assertIsNone(self.grant_repository.get(other_ledger_grant.uuid).revoked_at)

    def test_delete_inactive_before_removes_only_eligible_grants(self) -> None:
        user = self.create_user()
        old = self.create_grant(user, self.create_ledger())
        recent = self.create_grant(user, self.create_ledger())
        active = self.create_grant(user, self.create_ledger())
        self.grant_repository.revoke(old.uuid, 40)
        self.grant_repository.revoke(recent.uuid, 41)

        self.assertEqual(self.grant_repository.delete_inactive_before(40), 1)
        self.assertIsNone(self.grant_repository.get(old.uuid))
        self.assertIsNotNone(self.grant_repository.get(recent.uuid))
        self.assertIsNotNone(self.grant_repository.get(active.uuid))
