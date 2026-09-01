import sqlite3
from uuid import uuid4

from tests.integration.registry_repository_test_case import RegistryRepositoryTestCase


class SqliteRecoveryCodeRepositoryTest(RegistryRepositoryTestCase):
    def test_create_can_be_read_by_uuid_and_hash(self) -> None:
        user = self.create_user()

        code = self.recovery_code_repository.create(user.uuid, b"c" * 32, 30)

        self.assertEqual(self.recovery_code_repository.get(code.uuid), code)
        self.assertEqual(self.recovery_code_repository.get_by_code_hash(b"c" * 32), code)

    def test_create_requires_an_existing_user(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.recovery_code_repository.create(uuid4(), b"c" * 32, 30)

    def test_hash_is_unique_across_users(self) -> None:
        self.recovery_code_repository.create(self.create_user().uuid, b"c" * 32, 30)

        with self.assertRaises(sqlite3.IntegrityError):
            self.recovery_code_repository.create(self.create_user().uuid, b"c" * 32, 30)

    def test_consume_succeeds_only_once_and_not_before_creation(self) -> None:
        code = self.recovery_code_repository.create(self.create_user().uuid, b"c" * 32, 30)

        self.assertFalse(self.recovery_code_repository.consume(code.uuid, 29))
        self.assertTrue(self.recovery_code_repository.consume(code.uuid, 40))
        self.assertFalse(self.recovery_code_repository.consume(code.uuid, 50))
        consumed = self.recovery_code_repository.get(code.uuid)
        assert consumed is not None
        self.assertEqual(consumed.used_at, 40)

    def test_revoke_prevents_consumption_and_preserves_first_revocation(self) -> None:
        code = self.recovery_code_repository.create(self.create_user().uuid, b"c" * 32, 30)

        self.recovery_code_repository.revoke(code.uuid, 40)
        self.recovery_code_repository.revoke(code.uuid, 50)

        self.assertFalse(self.recovery_code_repository.consume(code.uuid, 60))
        revoked = self.recovery_code_repository.get(code.uuid)
        assert revoked is not None
        self.assertEqual(revoked.revoked_at, 40)
        self.assertIsNone(revoked.used_at)

    def test_used_code_cannot_be_revoked(self) -> None:
        code = self.recovery_code_repository.create(self.create_user().uuid, b"c" * 32, 30)
        self.recovery_code_repository.consume(code.uuid, 40)

        self.recovery_code_repository.revoke(code.uuid, 50)

        used = self.recovery_code_repository.get(code.uuid)
        assert used is not None
        self.assertEqual(used.used_at, 40)
        self.assertIsNone(used.revoked_at)

    def test_list_by_user_includes_used_revoked_and_available_codes(self) -> None:
        user = self.create_user()
        used = self.recovery_code_repository.create(user.uuid, b"a" * 32, 30)
        revoked = self.recovery_code_repository.create(user.uuid, b"b" * 32, 30)
        available = self.recovery_code_repository.create(user.uuid, b"c" * 32, 30)
        self.recovery_code_repository.create(self.create_user().uuid, b"d" * 32, 30)
        self.recovery_code_repository.consume(used.uuid, 40)
        self.recovery_code_repository.revoke(revoked.uuid, 40)

        self.assertCountEqual([code.uuid for code in self.recovery_code_repository.list_by_user(user.uuid)], [used.uuid, revoked.uuid, available.uuid])

    def test_delete_inactive_before_removes_only_eligible_codes(self) -> None:
        user = self.create_user()
        old = self.recovery_code_repository.create(user.uuid, b"a" * 32, 30)
        recent = self.recovery_code_repository.create(user.uuid, b"b" * 32, 30)
        active = self.recovery_code_repository.create(user.uuid, b"c" * 32, 30)
        self.recovery_code_repository.revoke(old.uuid, 40)
        self.recovery_code_repository.revoke(recent.uuid, 41)

        self.assertEqual(self.recovery_code_repository.delete_inactive_before(40), 1)
        self.assertIsNone(self.recovery_code_repository.get(old.uuid))
        self.assertIsNotNone(self.recovery_code_repository.get(recent.uuid))
        self.assertIsNotNone(self.recovery_code_repository.get(active.uuid))

    def test_delete_inactive_before_removes_used_codes(self) -> None:
        user = self.create_user()
        used = self.recovery_code_repository.create(user.uuid, b"u" * 32, 30)
        active = self.recovery_code_repository.create(user.uuid, b"a" * 32, 30)
        self.assertTrue(self.recovery_code_repository.consume(used.uuid, 40))

        self.assertEqual(self.recovery_code_repository.delete_inactive_before(40), 1)
        self.assertIsNone(self.recovery_code_repository.get(used.uuid))
        self.assertIsNotNone(self.recovery_code_repository.get(active.uuid))


if __name__ == "__main__":
    import unittest

    unittest.main()
