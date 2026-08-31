import sqlite3
from uuid import uuid4

from pydantic import ValidationError

from tests.integration.registry_repository_test_case import RegistryRepositoryTestCase


class SqliteWebAuthnCredentialRepositoryTest(RegistryRepositoryTestCase):
    def test_create_can_be_read_by_uuid_and_credential_id(self) -> None:
        user = self.create_user()

        credential = self.webauthn_repository.create(user.uuid, b"credential-id", b"public-key", 0, 30, "Phone")

        self.assertEqual(self.webauthn_repository.get(credential.uuid), credential)
        self.assertEqual(self.webauthn_repository.get_by_credential_id(b"credential-id"), credential)

    def test_create_requires_an_existing_user(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.webauthn_repository.create(uuid4(), b"credential-id", b"public-key", 0, 30, "Phone")

    def test_credential_id_is_unique_across_users(self) -> None:
        first_user = self.create_user()
        second_user = self.create_user()
        self.webauthn_repository.create(first_user.uuid, b"credential-id", b"first-key", 0, 30, "Phone")

        with self.assertRaises(sqlite3.IntegrityError):
            self.webauthn_repository.create(second_user.uuid, b"credential-id", b"second-key", 0, 30, "Laptop")

    def test_update_usage_changes_counter_and_last_use_together(self) -> None:
        user = self.create_user()
        credential = self.webauthn_repository.create(user.uuid, b"credential-id", b"public-key", 3, 30, "Phone")

        self.webauthn_repository.update_usage(credential.uuid, 4, 40)

        updated = self.webauthn_repository.get(credential.uuid)
        assert updated is not None
        self.assertEqual(updated.sign_count, 4)
        self.assertEqual(updated.last_used_at, 40)

    def test_update_usage_rejects_last_use_before_creation(self) -> None:
        user = self.create_user()
        credential = self.webauthn_repository.create(user.uuid, b"credential-id", b"public-key", 0, 30, "Phone")

        with self.assertRaises(ValidationError):
            self.webauthn_repository.update_usage(credential.uuid, 1, 29)

    def test_update_name_and_delete_affect_only_selected_credential(self) -> None:
        user = self.create_user()
        selected = self.webauthn_repository.create(user.uuid, b"selected", b"public-key", 0, 30, "Old")
        other = self.webauthn_repository.create(user.uuid, b"other", b"public-key", 0, 30, "Other")

        self.webauthn_repository.update_name(selected.uuid, "New")
        self.webauthn_repository.delete(selected.uuid)

        self.assertIsNone(self.webauthn_repository.get(selected.uuid))
        self.assertEqual(self.webauthn_repository.get(other.uuid), other)

    def test_list_by_user_excludes_other_users(self) -> None:
        first_user = self.create_user()
        second_user = self.create_user()
        first = self.webauthn_repository.create(first_user.uuid, b"first", b"key", 0, 30, "Phone")
        second = self.webauthn_repository.create(first_user.uuid, b"second", b"key", 0, 30, "Laptop")
        self.webauthn_repository.create(second_user.uuid, b"third", b"key", 0, 30, "Tablet")

        self.assertCountEqual([credential.uuid for credential in self.webauthn_repository.list_by_user(first_user.uuid)], [first.uuid, second.uuid])


if __name__ == "__main__":
    import unittest

    unittest.main()
