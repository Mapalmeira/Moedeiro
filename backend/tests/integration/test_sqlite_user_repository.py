import sqlite3

from pydantic import ValidationError

from tests.integration.registry_repository_test_case import RegistryRepositoryTestCase


class SqliteUserRepositoryTest(RegistryRepositoryTestCase):
    def test_create_derives_normalized_name_and_initial_password_timestamp(self) -> None:
        user = self.user_repository.create("  ＡLICE  ", "$argon2id$encoded", 20)

        self.assertEqual(user.normalized_name, "alice")
        self.assertEqual(user.password_changed_at, 20)
        self.assertEqual(self.user_repository.get(user.uuid), user)
        self.assertEqual(self.user_repository.get_by_normalized_name("alice"), user)

    def test_normalized_name_is_unique(self) -> None:
        self.create_user("Alice")

        with self.assertRaises(sqlite3.IntegrityError):
            self.user_repository.create("  ＡLICE ", "$argon2id$other", 20)

    def test_update_name_changes_display_and_normalized_name_together(self) -> None:
        user = self.create_user("Alice")

        self.user_repository.update_name(user.uuid, "  BÓB  ")

        updated = self.user_repository.get(user.uuid)
        assert updated is not None
        self.assertEqual(updated.name, "  BÓB  ")
        self.assertEqual(updated.normalized_name, "bób")

    def test_update_password_changes_hash_and_timestamp_together(self) -> None:
        user = self.create_user("Alice")

        self.assertTrue(self.user_repository.update_password(user.uuid, user.password_hash, "$argon2id$new", 30))

        updated = self.user_repository.get(user.uuid)
        assert updated is not None
        self.assertEqual(updated.password_hash, "$argon2id$new")
        self.assertEqual(updated.password_changed_at, 30)

    def test_update_password_rejects_timestamp_before_user_creation(self) -> None:
        user = self.create_user("Alice")

        with self.assertRaises(ValidationError):
            self.user_repository.update_password(user.uuid, user.password_hash, "$argon2id$new", 19)

    def test_update_password_rejects_a_stale_password_hash(self) -> None:
        user = self.create_user("Alice")

        self.assertFalse(self.user_repository.update_password(user.uuid, "$argon2id$stale", "$argon2id$new", 30))

        self.assertEqual(self.user_repository.get(user.uuid), user)

    def test_list_all_returns_every_user(self) -> None:
        first = self.create_user("Alice")
        second = self.create_user("Bob")

        self.assertCountEqual([user.uuid for user in self.user_repository.list_all()], [first.uuid, second.uuid])


if __name__ == "__main__":
    import unittest

    unittest.main()
