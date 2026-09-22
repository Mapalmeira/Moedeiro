import sqlite3
from uuid import uuid4

from tests.integration.registry_repository_test_case import RegistryRepositoryTestCase


class SqliteExternalAccessRepositoryTest(RegistryRepositoryTestCase):
    def test_create_returns_access_readable_by_uuid_and_hash_and_creates_grantee(self) -> None:
        user = self.create_user()

        access = self.external_access_repository.create(user.uuid, "Sync plugin", b"t" * 32)

        self.assertEqual(self.external_access_repository.get(access.uuid), access)
        self.assertEqual(self.external_access_repository.get_by_token_hash(b"t" * 32), access)
        grantee = self.connection.execute(
            "SELECT uuid FROM ledger_grantee WHERE uuid = ?",
            (access.uuid.bytes,),
        ).fetchone()
        self.assertEqual(tuple(grantee), (access.uuid.bytes,))

    def test_create_requires_existing_user(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.external_access_repository.create(uuid4(), "Sync plugin", b"t" * 32)

    def test_token_hash_is_unique(self) -> None:
        user = self.create_user()
        self.external_access_repository.create(user.uuid, "First", b"t" * 32)

        with self.assertRaises(sqlite3.IntegrityError):
            self.external_access_repository.create(user.uuid, "Second", b"t" * 32)

    def test_delete_ungranted_keeps_accesses_that_still_have_a_grant(self) -> None:
        user = self.create_user()
        ledger = self.create_ledger()
        orphan = self.external_access_repository.create(user.uuid, "Orphan", b"o" * 32)
        granted = self.external_access_repository.create(user.uuid, "Granted", b"g" * 32)
        self.grant_repository.create(granted.uuid, ledger.uuid, "GUEST", 30)

        self.assertEqual(self.external_access_repository.delete_ungranted(), 1)

        self.assertIsNone(self.external_access_repository.get(orphan.uuid))
        self.assertIsNone(
            self.connection.execute("SELECT uuid FROM ledger_grantee WHERE uuid = ?", (orphan.uuid.bytes,)).fetchone()
        )
        self.assertEqual(self.external_access_repository.get(granted.uuid), granted)

    def test_list_by_user_returns_only_that_users_accesses(self) -> None:
        user = self.create_user()
        other_user = self.create_user()
        second = self.external_access_repository.create(user.uuid, "Second", b"b" * 32)
        first = self.external_access_repository.create(user.uuid, "First", b"a" * 32)
        self.external_access_repository.create(other_user.uuid, "Other", b"o" * 32)

        self.assertEqual(self.external_access_repository.list_by_user(user.uuid), [first, second])

    def test_delete_removes_grantee_access_and_grants(self) -> None:
        user = self.create_user()
        ledger = self.create_ledger()
        access = self.external_access_repository.create(user.uuid, "Sync plugin", b"t" * 32)
        grant = self.grant_repository.create(access.uuid, ledger.uuid, "GUEST", 30)

        self.assertTrue(self.external_access_repository.delete(access.uuid))

        self.assertIsNone(self.external_access_repository.get(access.uuid))
        self.assertIsNone(self.grant_repository.get(grant.uuid))
        self.assertIsNone(self.connection.execute("SELECT uuid FROM ledger_grantee WHERE uuid = ?", (access.uuid.bytes,)).fetchone())
        self.assertFalse(self.external_access_repository.delete(access.uuid))
