import sqlite3
from uuid import uuid4

from app.domain.registry.model.mfa_method import TOTP_SETUP_TTL_SECONDS
from tests.integration.registry_repository_test_case import RegistryRepositoryTestCase


class SqliteMfaMethodRepositoryTest(RegistryRepositoryTestCase):
    def test_create_returns_a_totp_method_readable_by_uuid(self) -> None:
        user = self.create_user()

        method = self.mfa_repository.create(user.uuid, "TOTP", b"encrypted-secret", 30, 630)

        self.assertEqual(self.mfa_repository.get(method.uuid), method)

    def test_get_totp_by_user_returns_only_the_method_owned_by_the_user(self) -> None:
        user = self.create_user()
        other_user = self.create_user()
        method = self.mfa_repository.create(user.uuid, "TOTP", b"encrypted-secret", 30, 630)
        self.mfa_repository.create(other_user.uuid, "TOTP", b"other-secret", 30, 630)

        self.assertEqual(self.mfa_repository.get_totp_by_user(user.uuid), method)

    def test_is_totp_enabled_requires_a_confirmed_method_owned_by_the_user(self) -> None:
        user = self.create_user()
        other_user = self.create_user()
        pending = self.mfa_repository.create(user.uuid, "TOTP", b"pending", 30, 630)
        self.mfa_repository.create(other_user.uuid, "TOTP", b"other", 30, 630, 40)

        self.assertFalse(self.mfa_repository.is_totp_enabled(user.uuid))
        self.assertTrue(self.mfa_repository.confirm(pending.uuid, 40, 1))
        self.assertTrue(self.mfa_repository.is_totp_enabled(user.uuid))

    def test_confirm_activates_a_pending_method_only_once(self) -> None:
        method = self.mfa_repository.create(self.create_user().uuid, "TOTP", b"encrypted-secret", 30, 630)

        self.assertTrue(self.mfa_repository.confirm(method.uuid, 40, 1))
        self.assertFalse(self.mfa_repository.confirm(method.uuid, 50, 2))
        confirmed = self.mfa_repository.get(method.uuid)
        assert confirmed is not None
        self.assertEqual(confirmed.confirmed_at, 40)
        self.assertEqual(confirmed.last_used_counter, 1)

    def test_confirm_atomically_rejects_expired_pending_methods(self) -> None:
        for elapsed in (TOTP_SETUP_TTL_SECONDS, TOTP_SETUP_TTL_SECONDS + 1):
            method = self.mfa_repository.create(self.create_user().uuid, "TOTP", b"pending", 30, 30 + TOTP_SETUP_TTL_SECONDS)
            self.assertFalse(self.mfa_repository.confirm(method.uuid, 30 + elapsed, 1))
            self.assertIsNone(self.mfa_repository.get(method.uuid).confirmed_at)

    def test_use_totp_counter_accepts_only_a_later_counter(self) -> None:
        method = self.mfa_repository.create(self.create_user().uuid, "TOTP", b"encrypted-secret", 30, 630, 40, 1)

        self.assertTrue(self.mfa_repository.use_totp_counter(method.uuid, 2))
        self.assertFalse(self.mfa_repository.use_totp_counter(method.uuid, 2))
        self.assertFalse(self.mfa_repository.use_totp_counter(method.uuid, 1))

    def test_delete_unconfirmed_before_removes_only_pending_methods_at_the_cutoff(self) -> None:
        old = self.mfa_repository.create(self.create_user().uuid, "TOTP", b"old", 30, 40)
        recent = self.mfa_repository.create(self.create_user().uuid, "TOTP", b"recent", 30, 41)
        confirmed = self.mfa_repository.create(self.create_user().uuid, "TOTP", b"confirmed", 30, 630, 31)

        self.assertEqual(self.mfa_repository.delete_unconfirmed_before(40), 1)
        self.assertIsNone(self.mfa_repository.get(old.uuid))
        self.assertIsNotNone(self.mfa_repository.get(recent.uuid))
        self.assertIsNotNone(self.mfa_repository.get(confirmed.uuid))

    def test_create_requires_an_existing_user(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.mfa_repository.create(uuid4(), "TOTP", b"encrypted-secret", 30, 630)

    def test_user_can_have_only_one_totp_method(self) -> None:
        user = self.create_user()
        self.mfa_repository.create(user.uuid, "TOTP", b"first", 30, 630)

        with self.assertRaises(sqlite3.IntegrityError):
            self.mfa_repository.create(user.uuid, "TOTP", b"second", 40, 640)

    def test_list_by_user_excludes_other_users(self) -> None:
        first_user = self.create_user()
        second_user = self.create_user()
        first = self.mfa_repository.create(first_user.uuid, "TOTP", b"first", 30, 630)
        self.mfa_repository.create(second_user.uuid, "TOTP", b"second", 30, 630)

        self.assertEqual(self.mfa_repository.list_by_user(first_user.uuid), [first])

    def test_delete_removes_only_selected_method(self) -> None:
        first_user = self.create_user()
        second_user = self.create_user()
        selected = self.mfa_repository.create(first_user.uuid, "TOTP", b"first", 30, 630)
        other = self.mfa_repository.create(second_user.uuid, "TOTP", b"second", 30, 630)

        self.mfa_repository.delete(selected.uuid)

        self.assertIsNone(self.mfa_repository.get(selected.uuid))
        self.assertEqual(self.mfa_repository.get(other.uuid), other)


if __name__ == "__main__":
    import unittest

    unittest.main()
