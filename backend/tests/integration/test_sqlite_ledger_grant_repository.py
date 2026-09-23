import sqlite3
from uuid import uuid4

from tests.integration.registry_repository_test_case import RegistryRepositoryTestCase


class SqliteLedgerGrantRepositoryTest(RegistryRepositoryTestCase):
    def test_create_returns_an_owner_grant_readable_by_uuid_and_active_relation(self) -> None:
        user = self.create_user()
        ledger = self.create_ledger()

        grant = self.grant_repository.create(user.uuid, ledger.uuid, "OWNER", 30)

        self.assertEqual(self.grant_repository.get(grant.uuid), grant)
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
        ledger = self.create_ledger()
        first = self.create_external_guest_grant(ledger, "First", b"a" * 32)
        second = self.create_external_guest_grant(ledger, "Second", b"b" * 32)

        self.assertCountEqual(self.grant_repository.list_by_ledger(ledger.uuid), [first, second])

    def test_only_one_active_owner_exists_for_each_ledger(self) -> None:
        first_user = self.create_user()
        second_user = self.create_user()
        ledger = self.create_ledger()
        self.grant_repository.create(first_user.uuid, ledger.uuid, "OWNER", 30)

        with self.assertRaises(sqlite3.IntegrityError):
            self.grant_repository.create(second_user.uuid, ledger.uuid, "OWNER", 31)

    def test_one_grantee_cannot_have_multiple_active_grants_for_one_ledger(self) -> None:
        user = self.create_user()
        ledger = self.create_ledger()
        self.grant_repository.create(user.uuid, ledger.uuid, "GUEST", 30)

        with self.assertRaises(sqlite3.IntegrityError):
            self.grant_repository.create(user.uuid, ledger.uuid, "OWNER", 31)

    def test_get_active_by_grantee_and_ledger_returns_the_single_active_relation(self) -> None:
        user = self.create_user()
        ledger = self.create_ledger()
        old = self.grant_repository.create(user.uuid, ledger.uuid, "GUEST", 30)
        self.grant_repository.revoke(old.uuid, 40)
        active = self.grant_repository.create(user.uuid, ledger.uuid, "OWNER", 50)

        self.assertEqual(self.grant_repository.get_active_by_grantee_and_ledger(user.uuid, ledger.uuid), active)

    def test_revoked_owner_can_be_replaced(self) -> None:
        user = self.create_user()
        ledger = self.create_ledger()
        original = self.grant_repository.create(user.uuid, ledger.uuid, "OWNER", 30)
        self.grant_repository.revoke(original.uuid, 40)

        replacement = self.grant_repository.create(user.uuid, ledger.uuid, "OWNER", 50)

        self.assertEqual(self.grant_repository.get_active_owner_by_ledger(ledger.uuid), replacement)

    def test_revoke_is_idempotent_and_removes_active_relation(self) -> None:
        grant = self.create_owner_grant()

        self.grant_repository.revoke(grant.uuid, 40)
        self.grant_repository.revoke(grant.uuid, 50)

        revoked = self.grant_repository.get(grant.uuid)
        assert revoked is not None
        self.assertEqual(revoked.revoked_at, 40)
        self.assertIsNone(self.grant_repository.get_active_owner_by_ledger(grant.ledger_uuid))

    def test_list_methods_filter_by_grantee_and_ledger(self) -> None:
        first_user = self.create_user()
        second_user = self.create_user()
        first_ledger = self.create_ledger()
        second_ledger = self.create_ledger()
        owner = self.create_owner_grant(first_user, first_ledger)
        guest = self.create_external_guest_grant(first_ledger, "Plugin", b"p" * 32)
        second = self.create_owner_grant(first_user, second_ledger)
        third_ledger = self.create_ledger()
        third = self.create_owner_grant(second_user, third_ledger)

        self.assertCountEqual(self.grant_repository.list_by_grantee(first_user.uuid), [owner, second])
        self.assertEqual(self.grant_repository.list_by_grantee(guest.grantee_uuid), [guest])
        self.assertCountEqual(self.grant_repository.list_by_ledger(first_ledger.uuid), [owner, guest])
        self.assertEqual(self.grant_repository.list_by_grantee(second_user.uuid), [third])

    def test_list_grants_does_not_query_grantee_entities(self) -> None:
        user = self.create_user()
        ledger = self.create_ledger()
        owner = self.create_owner_grant(user, ledger)
        guest = self.create_external_guest_grant(ledger, "Sync plugin", b"t" * 32)
        statements: list[str] = []
        self.connection.set_trace_callback(statements.append)

        grants = self.grant_repository.list_by_ledger(ledger.uuid)

        self.connection.set_trace_callback(None)
        self.assertCountEqual(grants, [owner, guest])
        selects = [statement for statement in statements if statement.lstrip().upper().startswith("SELECT")]
        self.assertEqual(len(selects), 1)
        self.assertNotIn("JOIN", selects[0].upper())

    def test_delete_inactive_before_removes_only_eligible_grants(self) -> None:
        user = self.create_user()
        old = self.create_owner_grant(user, self.create_ledger())
        recent = self.create_owner_grant(user, self.create_ledger())
        active = self.create_owner_grant(user, self.create_ledger())
        self.grant_repository.revoke(old.uuid, 40)
        self.grant_repository.revoke(recent.uuid, 41)

        self.assertEqual(self.grant_repository.delete_inactive_before(40), 1)
        self.assertIsNone(self.grant_repository.get(old.uuid))
        self.assertIsNotNone(self.grant_repository.get(recent.uuid))
        self.assertIsNotNone(self.grant_repository.get(active.uuid))
