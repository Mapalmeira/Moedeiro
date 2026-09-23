import sqlite3

from tests.integration.registry_repository_test_case import RegistryRepositoryTestCase


class SqliteExternalAccessRepositoryTest(RegistryRepositoryTestCase):
    def test_create_returns_access_readable_by_uuid_and_hash_and_creates_grantee(self) -> None:
        access = self.external_access_repository.create("Sync plugin", b"t" * 32)

        self.assertEqual(self.external_access_repository.get(access.uuid), access)
        self.assertEqual(self.external_access_repository.get_by_token_hash(b"t" * 32), access)
        grantee = self.connection.execute(
            "SELECT uuid FROM ledger_grantee WHERE uuid = ?",
            (access.uuid.bytes,),
        ).fetchone()
        self.assertEqual(tuple(grantee), (access.uuid.bytes,))

    def test_token_hash_is_unique(self) -> None:
        self.external_access_repository.create("First", b"t" * 32)

        with self.assertRaises(sqlite3.IntegrityError):
            self.external_access_repository.create("Second", b"t" * 32)

    def test_delete_ungranted_keeps_accesses_that_still_have_a_grant(self) -> None:
        ledger = self.create_ledger()
        orphan = self.external_access_repository.create("Orphan", b"o" * 32)
        granted = self.external_access_repository.create("Granted", b"g" * 32)
        self.grant_repository.create(granted.uuid, ledger.uuid, "GUEST", 30)

        self.assertEqual(self.external_access_repository.delete_ungranted(), 1)

        self.assertIsNone(self.external_access_repository.get(orphan.uuid))
        self.assertIsNone(
            self.connection.execute("SELECT uuid FROM ledger_grantee WHERE uuid = ?", (orphan.uuid.bytes,)).fetchone()
        )
        self.assertEqual(self.external_access_repository.get(granted.uuid), granted)

    def test_list_all_orders_by_name_then_uuid(self) -> None:
        second = self.external_access_repository.create("Second", b"b" * 32)
        first = self.external_access_repository.create("First", b"a" * 32)

        self.assertEqual(self.external_access_repository.list_all(), [first, second])

    def test_delete_removes_grantee_access_and_grants(self) -> None:
        ledger = self.create_ledger()
        access = self.external_access_repository.create("Sync plugin", b"t" * 32)
        grant = self.grant_repository.create(access.uuid, ledger.uuid, "GUEST", 30)

        self.assertTrue(self.external_access_repository.delete(access.uuid))

        self.assertIsNone(self.external_access_repository.get(access.uuid))
        self.assertIsNone(self.grant_repository.get(grant.uuid))
        self.assertIsNone(self.connection.execute("SELECT uuid FROM ledger_grantee WHERE uuid = ?", (access.uuid.bytes,)).fetchone())
        self.assertFalse(self.external_access_repository.delete(access.uuid))
