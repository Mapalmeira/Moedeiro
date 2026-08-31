import sqlite3
from uuid import uuid4

from tests.integration.registry_repository_test_case import RegistryRepositoryTestCase


class SqliteMfaMethodRepositoryTest(RegistryRepositoryTestCase):
    def test_create_returns_a_totp_method_readable_by_uuid(self) -> None:
        user = self.create_user()

        method = self.mfa_repository.create(user.uuid, "TOTP", b"encrypted-secret", 30)

        self.assertEqual(self.mfa_repository.get(method.uuid), method)

    def test_create_requires_an_existing_user(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.mfa_repository.create(uuid4(), "TOTP", b"encrypted-secret", 30)

    def test_list_by_user_excludes_other_users(self) -> None:
        first_user = self.create_user()
        second_user = self.create_user()
        first = self.mfa_repository.create(first_user.uuid, "TOTP", b"first", 30)
        self.mfa_repository.create(second_user.uuid, "TOTP", b"second", 30)

        self.assertEqual(self.mfa_repository.list_by_user(first_user.uuid), [first])

    def test_delete_removes_only_selected_method(self) -> None:
        first_user = self.create_user()
        second_user = self.create_user()
        selected = self.mfa_repository.create(first_user.uuid, "TOTP", b"first", 30)
        other = self.mfa_repository.create(second_user.uuid, "TOTP", b"second", 30)

        self.mfa_repository.delete(selected.uuid)

        self.assertIsNone(self.mfa_repository.get(selected.uuid))
        self.assertEqual(self.mfa_repository.get(other.uuid), other)


if __name__ == "__main__":
    import unittest

    unittest.main()
