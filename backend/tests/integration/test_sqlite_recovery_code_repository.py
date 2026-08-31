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

    def test_list_by_user_includes_used_and_unused_codes(self) -> None:
        user = self.create_user()
        used = self.recovery_code_repository.create(user.uuid, b"a" * 32, 30)
        unused = self.recovery_code_repository.create(user.uuid, b"b" * 32, 30)
        self.recovery_code_repository.create(self.create_user().uuid, b"c" * 32, 30)
        self.recovery_code_repository.consume(used.uuid, 40)

        self.assertCountEqual([code.uuid for code in self.recovery_code_repository.list_by_user(user.uuid)], [used.uuid, unused.uuid])


if __name__ == "__main__":
    import unittest

    unittest.main()
