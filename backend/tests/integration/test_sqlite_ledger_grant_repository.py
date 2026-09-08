import sqlite3
from uuid import uuid4

from tests.integration.registry_repository_test_case import RegistryRepositoryTestCase


class SqliteLedgerGrantRepositoryTest(RegistryRepositoryTestCase):
    def test_create_returns_an_owner_grant_readable_by_uuid_and_active_relation(self) -> None:
        user = self.create_user()
        ledger = self.create_ledger()

        grant = self.grant_repository.create(user.uuid, ledger.uuid, "OWNER", 30)

        self.assertEqual(self.grant_repository.get(grant.uuid), grant)
        self.assertEqual(self.grant_repository.get_active(user.uuid, ledger.uuid), grant)

    def test_create_requires_existing_user_and_ledger(self) -> None:
        user = self.create_user()
        ledger = self.create_ledger()
        invalid_relations = ((uuid4(), ledger.uuid), (user.uuid, uuid4()))

        for user_uuid, ledger_uuid in invalid_relations:
            with self.subTest(user_uuid=user_uuid, ledger_uuid=ledger_uuid):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.grant_repository.create(user_uuid, ledger_uuid, "OWNER", 30)

    def test_only_one_active_grant_exists_for_each_user_and_ledger(self) -> None:
        user = self.create_user()
        ledger = self.create_ledger()
        self.grant_repository.create(user.uuid, ledger.uuid, "OWNER", 30)

        with self.assertRaises(sqlite3.IntegrityError):
            self.grant_repository.create(user.uuid, ledger.uuid, "OWNER", 31)

    def test_only_one_active_owner_exists_for_each_ledger(self) -> None:
        first_user = self.create_user()
        second_user = self.create_user()
        ledger = self.create_ledger()
        self.grant_repository.create(first_user.uuid, ledger.uuid, "OWNER", 30)

        with self.assertRaises(sqlite3.IntegrityError):
            self.grant_repository.create(second_user.uuid, ledger.uuid, "OWNER", 31)

    def test_revoked_grant_can_be_replaced(self) -> None:
        user = self.create_user()
        ledger = self.create_ledger()
        original = self.grant_repository.create(user.uuid, ledger.uuid, "OWNER", 30)
        self.grant_repository.revoke(original.uuid, 40)

        replacement = self.grant_repository.create(user.uuid, ledger.uuid, "OWNER", 50)

        self.assertEqual(self.grant_repository.get_active(user.uuid, ledger.uuid), replacement)

    def test_revoke_is_idempotent_and_removes_active_relation(self) -> None:
        grant = self.create_grant()

        self.grant_repository.revoke(grant.uuid, 40)
        self.grant_repository.revoke(grant.uuid, 50)

        revoked = self.grant_repository.get(grant.uuid)
        assert revoked is not None
        self.assertEqual(revoked.revoked_at, 40)
        self.assertIsNone(self.grant_repository.get_active(grant.user_uuid, grant.ledger_uuid))

    def test_list_methods_filter_each_side_of_relation(self) -> None:
        first_user = self.create_user()
        second_user = self.create_user()
        first_ledger = self.create_ledger()
        second_ledger = self.create_ledger()
        first = self.create_grant(first_user, first_ledger)
        second = self.create_grant(first_user, second_ledger)
        third_ledger = self.create_ledger()
        third = self.create_grant(second_user, third_ledger)

        self.assertCountEqual([grant.uuid for grant in self.grant_repository.list_by_user(first_user.uuid)], [first.uuid, second.uuid])
        self.assertEqual(self.grant_repository.list_by_ledger(first_ledger.uuid), [first])
        self.assertEqual(self.grant_repository.list_by_user(second_user.uuid), [third])

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


if __name__ == "__main__":
    import unittest

    unittest.main()
