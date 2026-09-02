import sqlite3
from uuid import uuid4

from tests.integration.registry_repository_test_case import RegistryRepositoryTestCase


class SqliteRecoveryCodeRepositoryTest(RegistryRepositoryTestCase):
    def test_create_can_be_read_by_uuid_and_as_the_users_active_code(self) -> None:
        user = self.create_user()

        code = self.recovery_code_repository.create(user.uuid, b"c" * 32, 30, 130)

        self.assertEqual(self.recovery_code_repository.get(code.uuid), code)
        self.assertEqual(self.recovery_code_repository.get_active_by_user(user.uuid, 30), code)

    def test_create_requires_an_existing_user(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.recovery_code_repository.create(uuid4(), b"c" * 32, 30, 130)

    def test_hash_is_unique_across_users(self) -> None:
        self.recovery_code_repository.create(self.create_user().uuid, b"c" * 32, 30, 130)

        with self.assertRaises(sqlite3.IntegrityError):
            self.recovery_code_repository.create(self.create_user().uuid, b"c" * 32, 30, 130)

    def test_only_one_code_can_be_active_for_a_user(self) -> None:
        user = self.create_user()
        self.recovery_code_repository.create(user.uuid, b"a" * 32, 30, 130)

        with self.assertRaises(sqlite3.IntegrityError):
            self.recovery_code_repository.create(user.uuid, b"b" * 32, 31, 131)

    def test_consume_succeeds_only_once_and_not_before_creation(self) -> None:
        code = self.recovery_code_repository.create(self.create_user().uuid, b"c" * 32, 30, 130)

        self.assertFalse(self.recovery_code_repository.consume(code.uuid, 29))
        self.assertTrue(self.recovery_code_repository.consume(code.uuid, 40))
        self.assertFalse(self.recovery_code_repository.consume(code.uuid, 50))
        consumed = self.recovery_code_repository.get(code.uuid)
        assert consumed is not None
        self.assertEqual(consumed.used_at, 40)

    def test_delete_active_by_user_preserves_used_codes(self) -> None:
        user = self.create_user()
        used = self.recovery_code_repository.create(user.uuid, b"a" * 32, 30, 130)
        self.recovery_code_repository.consume(used.uuid, 40)
        active = self.recovery_code_repository.create(user.uuid, b"b" * 32, 41, 141)

        self.assertEqual(self.recovery_code_repository.delete_active_by_user(user.uuid), 1)
        self.assertIsNotNone(self.recovery_code_repository.get(used.uuid))
        self.assertIsNone(self.recovery_code_repository.get(active.uuid))

    def test_list_by_user_includes_used_and_active_codes(self) -> None:
        user = self.create_user()
        used = self.recovery_code_repository.create(user.uuid, b"a" * 32, 30, 130)
        self.recovery_code_repository.consume(used.uuid, 40)
        active = self.recovery_code_repository.create(user.uuid, b"b" * 32, 41, 141)
        self.recovery_code_repository.create(self.create_user().uuid, b"c" * 32, 41, 141)

        self.assertCountEqual([code.uuid for code in self.recovery_code_repository.list_by_user(user.uuid)], [used.uuid, active.uuid])

    def test_delete_inactive_before_removes_used_codes(self) -> None:
        user = self.create_user()
        used = self.recovery_code_repository.create(user.uuid, b"u" * 32, 30, 130)
        self.assertTrue(self.recovery_code_repository.consume(used.uuid, 40))
        active = self.recovery_code_repository.create(user.uuid, b"a" * 32, 41, 141)

        self.assertEqual(self.recovery_code_repository.delete_inactive_before(40), 1)
        self.assertIsNone(self.recovery_code_repository.get(used.uuid))
        self.assertIsNotNone(self.recovery_code_repository.get(active.uuid))

    def test_expired_code_is_not_active_and_is_removed_by_cleanup(self) -> None:
        code = self.recovery_code_repository.create(self.create_user().uuid, b"c" * 32, 30, 40)

        self.assertIsNone(self.recovery_code_repository.get_active_by_user(code.user_uuid, 40))
        self.assertFalse(self.recovery_code_repository.consume(code.uuid, 40))
        self.assertEqual(self.recovery_code_repository.delete_inactive_before(40), 1)


if __name__ == "__main__":
    import unittest

    unittest.main()
