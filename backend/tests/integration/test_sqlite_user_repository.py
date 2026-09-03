import sqlite3

from pydantic import ValidationError

from tests.integration.registry_repository_test_case import RegistryRepositoryTestCase


class SqliteUserRepositoryTest(RegistryRepositoryTestCase):
    def test_create_derives_normalized_name_and_initial_password_timestamp(self) -> None:
        user = self.user_repository.create("Alice", "$argon2id$encoded", 20)

        self.assertEqual(user.normalized_name, "alice")
        self.assertEqual(user.password_changed_at, 20)
        self.assertEqual(self.user_repository.get(user.uuid), user)
        self.assertEqual(self.user_repository.get_by_normalized_name("alice"), user)

    def test_normalized_name_is_unique(self) -> None:
        self.create_user("Alice")

        with self.assertRaises(sqlite3.IntegrityError):
            self.user_repository.create("ALICE", "$argon2id$other", 20)

    def test_update_name_changes_display_and_normalized_name_together(self) -> None:
        user = self.create_user("Alice")

        self.user_repository.update_name(user.uuid, "Bob")

        updated = self.user_repository.get(user.uuid)
        assert updated is not None
        self.assertEqual(updated.name, "Bob")
        self.assertEqual(updated.normalized_name, "bob")

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

    def test_list_all_orders_every_user_and_rejects_uuid_sorting(self) -> None:
        self.create_user("Alice")
        self.create_user("Bob")

        self.assertEqual([user.name for user in self.user_repository.list_all("name", False)], ["Bob", "Alice"])
        for sort_key in ("uuid", "password_changed_at", "last_accessed"):
            with self.subTest(sort_key=sort_key):
                with self.assertRaises(ValueError):
                    self.user_repository.list_all(sort_key, True)



if __name__ == "__main__":
    import unittest

    unittest.main()
