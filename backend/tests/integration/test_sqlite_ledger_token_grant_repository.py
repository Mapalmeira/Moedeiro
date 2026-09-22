import sqlite3

from pydantic import ValidationError

from tests.integration.registry_repository_test_case import RegistryRepositoryTestCase


class SqliteLedgerTokenGrantRepositoryTest(RegistryRepositoryTestCase):
    def test_create_returns_token_grant_with_parent_grant_readable_by_uuid_and_hash(self) -> None:
        grant = self.create_grant(type="EXTERNAL_ACCESS")

        token_grant = self.token_grant_repository.create(grant, "Sync plugin", b"t" * 32)

        self.assertEqual(token_grant.grant, grant)
        self.assertEqual(self.token_grant_repository.get(grant.uuid), token_grant)
        self.assertEqual(self.token_grant_repository.get_by_token_hash(b"t" * 32), token_grant)

    def test_create_requires_external_access_grant(self) -> None:
        owner = self.create_grant()

        with self.assertRaises(ValidationError):
            self.token_grant_repository.create(owner, "Invalid", b"t" * 32)

    def test_token_hash_is_unique(self) -> None:
        first = self.create_grant(type="EXTERNAL_ACCESS")
        second = self.create_grant(type="EXTERNAL_ACCESS")
        self.token_grant_repository.create(first, "First", b"t" * 32)

        with self.assertRaises(sqlite3.IntegrityError):
            self.token_grant_repository.create(second, "Second", b"t" * 32)

    def test_deleting_parent_grant_cascades_token_grant(self) -> None:
        grant = self.create_grant(type="EXTERNAL_ACCESS")
        self.token_grant_repository.create(grant, "Sync plugin", b"t" * 32)
        self.grant_repository.revoke(grant.uuid, 40)

        self.grant_repository.delete_inactive_before(40)

        self.assertIsNone(self.token_grant_repository.get(grant.uuid))
