import unittest
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

from app.application.registry.exceptions import InvalidCurrentPasswordError, InvalidTotpCodeError, LedgerGrantNotFoundError, LedgerNotFoundError, TotpCodeAlreadyUsedError, TotpRequiredError
from app.application.registry.use_cases.grant import create_external_ledger_grant, list_ledger_grants, revoke_ledger_grant, revoke_owned_ledger_grant, set_ledger_owner
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.registry.unit_of_work import SqliteRegistryUnitOfWork
from tests.fakes import FakePasswordHasher, FakeTotpAuthenticator


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"


class LedgerGrantUseCasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.database = SqliteDatabase.initialize(Path(self.temporary_directory.name) / "registry.sqlite", SCHEMA_PATH)
        self.password_hasher = FakePasswordHasher()
        self.totp_authenticator = FakeTotpAuthenticator()
        with self.open_registry() as unit_of_work:
            self.user = unit_of_work.user_repository.create("Alice", self.password_hasher.hash("current password"), 10)
            self.ledger = unit_of_work.ledger_repository.create(
                uuid4(),
                "Ledger",
                "ledger.sqlite",
                "lucide:BookOpen",
                b"\x80\x80\x80",
                10,
            )
            self.owner_grant = unit_of_work.ledger_grant_repository.create(self.user.uuid, self.ledger.uuid, "OWNER", 10)
            unit_of_work.commit()
        self.password_hasher.passwords.clear()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def open_registry(self) -> SqliteRegistryUnitOfWork:
        return SqliteRegistryUnitOfWork(self.database)

    def enable_totp(self) -> None:
        with self.open_registry() as unit_of_work:
            unit_of_work.mfa_method_repository.create(self.user.uuid, "TOTP", b"FAKESECRET", 10, 610, 10)
            unit_of_work.commit()

    @patch("app.application.registry.use_cases.grant.secrets.token_urlsafe", return_value="external-token")
    def test_create_external_grant_persists_only_the_token_hash(self, token_urlsafe) -> None:
        grant, token = create_external_ledger_grant(
            self.open_registry,
            self.password_hasher,
            self.user,
            self.ledger.uuid,
            "Sync plugin",
            "current password",
            20,
        )

        self.assertEqual(token, "external-token")
        self.assertEqual(grant.ledger_uuid, self.ledger.uuid)
        self.assertEqual(grant.role, "GUEST")
        with self.open_registry() as unit_of_work:
            stored = unit_of_work.ledger_grant_repository.get(grant.uuid)
            access = unit_of_work.external_access_repository.get(grant.grantee_uuid)
        self.assertEqual(stored, grant)
        assert access is not None
        self.assertEqual(access.user_uuid, self.user.uuid)
        self.assertEqual(access.name, "Sync plugin")
        self.assertEqual(access.token_hash, hashlib.sha256(b"external-token").digest())
        token_urlsafe.assert_called_once_with(32)

    def test_create_external_grant_requires_current_ownership(self) -> None:
        with self.open_registry() as unit_of_work:
            other_ledger = unit_of_work.ledger_repository.create(
                uuid4(),
                "Other",
                "other.sqlite",
                "lucide:BookOpen",
                b"\x80\x80\x80",
                10,
            )
            unit_of_work.commit()

        with self.assertRaises(LedgerNotFoundError):
            create_external_ledger_grant(
                self.open_registry,
                self.password_hasher,
                self.user,
                other_ledger.uuid,
                "Sync plugin",
                "current password",
                20,
            )

    def test_create_external_grant_rejects_invalid_password_before_writing(self) -> None:
        with self.assertRaises(InvalidCurrentPasswordError):
            create_external_ledger_grant(
                self.open_registry,
                self.password_hasher,
                self.user,
                self.ledger.uuid,
                "Sync plugin",
                "wrong password",
                20,
            )

        with self.open_registry() as unit_of_work:
            guest_grants = [grant for grant in unit_of_work.ledger_grant_repository.list_by_ledger(self.ledger.uuid) if grant.role == "GUEST"]
        self.assertEqual(guest_grants, [])

    def test_create_external_grant_enforces_totp_when_enabled(self) -> None:
        self.enable_totp()

        with self.assertRaises(TotpRequiredError):
            create_external_ledger_grant(
                self.open_registry,
                self.password_hasher,
                self.user,
                self.ledger.uuid,
                "Sync plugin",
                "current password",
                20,
                self.totp_authenticator,
            )
        with self.assertRaises(InvalidTotpCodeError):
            create_external_ledger_grant(
                self.open_registry,
                self.password_hasher,
                self.user,
                self.ledger.uuid,
                "Sync plugin",
                "current password",
                20,
                self.totp_authenticator,
                "000000",
            )

    def test_list_grants_returns_owner_and_external_access_as_ledger_grants(self) -> None:
        guest, _ = create_external_ledger_grant(
            self.open_registry,
            self.password_hasher,
            self.user,
            self.ledger.uuid,
            "Sync plugin",
            "current password",
            20,
        )

        owner_grants = list_ledger_grants(self.open_registry, self.user.uuid, self.ledger.uuid)
        guest_grants = list_ledger_grants(self.open_registry, guest.grantee_uuid, self.ledger.uuid)

        self.assertEqual(owner_grants, [self.owner_grant])
        self.assertEqual(guest_grants, [guest])

    def test_revoke_owned_guest_requires_password_and_totp_and_preserves_owner(self) -> None:
        self.enable_totp()
        self.totp_authenticator.fixed_counter = 7
        guest, _ = create_external_ledger_grant(
            self.open_registry,
            self.password_hasher,
            self.user,
            self.ledger.uuid,
            "Sync plugin",
            "current password",
            20,
            self.totp_authenticator,
            "123456",
        )

        with self.assertRaises(InvalidCurrentPasswordError):
            revoke_owned_ledger_grant(
                self.open_registry,
                self.password_hasher,
                self.user,
                guest.uuid,
                "wrong password",
                21,
                self.totp_authenticator,
                "123456",
            )
        with self.assertRaises(TotpRequiredError):
            revoke_owned_ledger_grant(
                self.open_registry,
                self.password_hasher,
                self.user,
                guest.uuid,
                "current password",
                21,
                self.totp_authenticator,
            )
        with self.assertRaises(TotpCodeAlreadyUsedError):
            revoke_owned_ledger_grant(
                self.open_registry,
                self.password_hasher,
                self.user,
                guest.uuid,
                "current password",
                21,
                self.totp_authenticator,
                "123456",
            )

        self.totp_authenticator.fixed_counter = 8
        revoke_owned_ledger_grant(
            self.open_registry,
            self.password_hasher,
            self.user,
            guest.uuid,
            "current password",
            21,
            self.totp_authenticator,
            "123456",
        )

        with self.open_registry() as unit_of_work:
            revoked = unit_of_work.ledger_grant_repository.get(guest.uuid)
            owner = unit_of_work.ledger_grant_repository.get_active_owner_by_ledger(self.ledger.uuid)
        assert revoked is not None
        self.assertEqual(revoked.revoked_at, 21)
        self.assertIsNotNone(owner)

    def test_user_cannot_revoke_another_users_guest_grant(self) -> None:
        guest, _ = create_external_ledger_grant(
            self.open_registry,
            self.password_hasher,
            self.user,
            self.ledger.uuid,
            "Sync plugin",
            "current password",
            20,
        )
        other_hasher = FakePasswordHasher()
        with self.open_registry() as unit_of_work:
            other = unit_of_work.user_repository.create("Bob", other_hasher.hash("other password"), 10)
            unit_of_work.commit()

        with self.assertRaises(LedgerGrantNotFoundError):
            revoke_owned_ledger_grant(
                self.open_registry,
                other_hasher,
                other,
                guest.uuid,
                "other password",
                21,
            )

    def test_owner_can_revoke_a_guest_without_resolving_the_grantee_type(self) -> None:
        with self.open_registry() as unit_of_work:
            guest_user = unit_of_work.user_repository.create("Bob", "$argon2id$test", 10)
            guest = unit_of_work.ledger_grant_repository.create(guest_user.uuid, self.ledger.uuid, "GUEST", 20)
            unit_of_work.commit()

        revoke_owned_ledger_grant(
            self.open_registry,
            self.password_hasher,
            self.user,
            guest.uuid,
            "current password",
            21,
        )

        with self.open_registry() as unit_of_work:
            revoked = unit_of_work.ledger_grant_repository.get(guest.uuid)
        assert revoked is not None
        self.assertEqual(revoked.revoked_at, 21)

    def test_owner_cannot_be_revoked_through_owned_guest_operation(self) -> None:
        with self.assertRaises(LedgerGrantNotFoundError):
            revoke_owned_ledger_grant(
                self.open_registry,
                self.password_hasher,
                self.user,
                self.owner_grant.uuid,
                "current password",
                21,
            )

    def test_setting_a_new_owner_revokes_previous_owner_and_guest_grants(self) -> None:
        first, _ = create_external_ledger_grant(
            self.open_registry,
            self.password_hasher,
            self.user,
            self.ledger.uuid,
            "First",
            "current password",
            20,
        )
        second, _ = create_external_ledger_grant(
            self.open_registry,
            self.password_hasher,
            self.user,
            self.ledger.uuid,
            "Second",
            "current password",
            21,
        )
        with self.open_registry() as unit_of_work:
            new_owner = unit_of_work.user_repository.create("Bob", "$argon2id$test$other password", 10)
            other_guest = unit_of_work.ledger_grant_repository.create(new_owner.uuid, self.ledger.uuid, "GUEST", 22)
            unit_of_work.commit()

        new_owner_grant = set_ledger_owner(self.open_registry, new_owner.uuid, self.ledger.uuid, 30)

        with self.open_registry() as unit_of_work:
            old_owner = unit_of_work.ledger_grant_repository.get(self.owner_grant.uuid)
            first_grant = unit_of_work.ledger_grant_repository.get(first.uuid)
            second_grant = unit_of_work.ledger_grant_repository.get(second.uuid)
            other_guest_grant = unit_of_work.ledger_grant_repository.get(other_guest.uuid)
        assert old_owner is not None and first_grant is not None and second_grant is not None and other_guest_grant is not None
        self.assertEqual(old_owner.revoked_at, 30)
        self.assertEqual(first_grant.revoked_at, 30)
        self.assertEqual(second_grant.revoked_at, 30)
        self.assertEqual(other_guest_grant.revoked_at, 30)
        self.assertEqual(new_owner_grant.role, "OWNER")
        self.assertEqual(new_owner_grant.grantee_uuid, new_owner.uuid)

    def test_revoking_owner_revokes_its_guest_grants(self) -> None:
        guest, _ = create_external_ledger_grant(
            self.open_registry,
            self.password_hasher,
            self.user,
            self.ledger.uuid,
            "Sync plugin",
            "current password",
            20,
        )

        revoke_ledger_grant(self.open_registry, self.owner_grant.uuid, 30)

        with self.open_registry() as unit_of_work:
            owner = unit_of_work.ledger_grant_repository.get(self.owner_grant.uuid)
            external = unit_of_work.ledger_grant_repository.get(guest.uuid)
        assert owner is not None and external is not None
        self.assertEqual(owner.revoked_at, 30)
        self.assertEqual(external.revoked_at, 30)
