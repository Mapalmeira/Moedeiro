from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.application.ledger.exceptions import LedgerNotFoundError
from app.application.registry.exceptions import LedgerLimitReachedError
from app.application.ledger.use_cases.ledger import access_owned_ledger, create_ledger, delete_owned_ledger, get_owned_ledger, list_owned_ledgers, update_owned_ledger
from app.infrastructure.persistence.sqlite.databases import SqliteDatabases


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class LedgerLifecycleUseCasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        directory = Path(self.temporary_directory.name)
        self.databases = SqliteDatabases(
            directory / "registry/registry.sqlite",
            REGISTRY_SCHEMA_PATH,
            directory / "ledgers",
            LEDGER_SCHEMA_PATH,
        )
        self.databases.initialize()
        with self.databases.open_registry() as unit_of_work:
            self.user = unit_of_work.user_repository.create("Alice", "$argon2id$test", 10)
            self.other_user = unit_of_work.user_repository.create("Bob", "$argon2id$test", 10)
            unit_of_work.commit()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def create(self, user_uuid=None, name="Household"):
        return create_ledger(
            self.databases.open_registry,
            self.databases.initialize_ledger,
            self.databases.delete_ledger_database,
            self.user.uuid if user_uuid is None else user_uuid,
            name,
            "lucide:WalletCards",
            b"\x10\x20\x30",
            100,
        )

    def test_create_materializes_registry_grant_database_and_metadata(self) -> None:
        ledger = self.create()

        self.assertEqual(ledger.path, f"{ledger.uuid}.sqlite")
        self.assertEqual(ledger.last_accessed_at, 100)
        with self.databases.open_registry() as unit_of_work:
            self.assertEqual(unit_of_work.ledger_repository.get(ledger.uuid), ledger)
            grant = unit_of_work.ledger_grant_repository.get_active(self.user.uuid, ledger.uuid)
        assert grant is not None
        self.assertEqual(grant.role, "OWNER")
        self.assertEqual(grant.created_at, 100)
        with self.databases.open_ledger(ledger.path) as unit_of_work:
            metadata = unit_of_work.ledger_metadata_repository.get()
        assert metadata is not None
        self.assertEqual(metadata.ledger_uuid, ledger.uuid)
        self.assertEqual(metadata.schema_version, 1)
        self.assertEqual(metadata.created_at, 100)

    def test_creation_limit_is_per_user_and_can_be_reused_after_deletion(self) -> None:
        with patch("app.application.ledger.use_cases.ledger.MAXIMUM_LEDGERS_PER_USER", 1):
            first = self.create()
            with self.assertRaises(LedgerLimitReachedError):
                self.create(name="Overflow")
            other = self.create(self.other_user.uuid, "Other")
            delete_owned_ledger(self.databases.open_registry, self.databases.delete_ledger_database, self.user.uuid, first.uuid)
            replacement = self.create(name="Replacement")

        self.assertEqual(list_owned_ledgers(self.databases.open_registry, self.user.uuid, "name", True), [replacement])
        self.assertEqual(list_owned_ledgers(self.databases.open_registry, self.other_user.uuid, "name", True), [other])

    def test_create_removes_database_and_rolls_back_registry_when_grant_creation_fails(self) -> None:
        with patch(
            "app.infrastructure.persistence.sqlite.registry.repository.ledger_grant.SqliteLedgerGrantRepository.create",
            side_effect=RuntimeError("grant failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "grant failed"):
                self.create()

        with self.databases.open_registry() as unit_of_work:
            self.assertEqual(unit_of_work.ledger_repository.list_all("name", True), [])
        self.assertEqual(list(self.databases.ledger_dbs_dir.iterdir()), [])

    def test_list_and_get_expose_only_ledgers_owned_by_the_user(self) -> None:
        owned = self.create(name="Owned")
        other = self.create(self.other_user.uuid, "Other")

        self.assertEqual(list_owned_ledgers(self.databases.open_registry, self.user.uuid, "name", True), [owned])
        self.assertEqual(get_owned_ledger(self.databases.open_registry, self.user.uuid, owned.uuid), owned)
        with self.assertRaises(LedgerNotFoundError):
            get_owned_ledger(self.databases.open_registry, self.user.uuid, other.uuid)

    def test_revoked_grant_stops_access_and_listing(self) -> None:
        ledger = self.create()
        with self.databases.open_registry() as unit_of_work:
            grant = unit_of_work.ledger_grant_repository.get_active(self.user.uuid, ledger.uuid)
            assert grant is not None
            unit_of_work.ledger_grant_repository.revoke(grant.uuid, 110)
            unit_of_work.commit()

        self.assertEqual(list_owned_ledgers(self.databases.open_registry, self.user.uuid, "name", True), [])
        with self.assertRaises(LedgerNotFoundError):
            get_owned_ledger(self.databases.open_registry, self.user.uuid, ledger.uuid)

    def test_access_updates_the_ledger_timestamp_without_affecting_other_ledgers(self) -> None:
        accessed = self.create(name="Accessed")
        untouched = self.create(name="Untouched")

        result = access_owned_ledger(self.databases.open_registry, self.user.uuid, accessed.uuid, 120)

        self.assertEqual(result.last_accessed_at, 120)
        self.assertEqual(get_owned_ledger(self.databases.open_registry, self.user.uuid, accessed.uuid).last_accessed_at, 120)
        self.assertEqual(get_owned_ledger(self.databases.open_registry, self.user.uuid, untouched.uuid).last_accessed_at, 100)
        self.assertEqual(list_owned_ledgers(self.databases.open_registry, self.user.uuid, "last_accessed_at", False), [result, untouched])

    def test_update_changes_public_properties_without_changing_identity_or_path(self) -> None:
        original = self.create()

        updated = update_owned_ledger(
            self.databases.open_registry,
            self.user.uuid,
            original.uuid,
            "Personal",
            "lucide:PiggyBank",
            b"\xaa\xbb\xcc",
            120,
        )

        self.assertEqual(updated.uuid, original.uuid)
        self.assertEqual(updated.path, original.path)
        self.assertEqual(updated.name, "Personal")
        self.assertEqual(updated.icon, "lucide:PiggyBank")
        self.assertEqual(updated.color_code, b"\xaa\xbb\xcc")
        self.assertEqual(get_owned_ledger(self.databases.open_registry, self.user.uuid, original.uuid), updated)

    def test_update_and_delete_reject_a_user_without_an_active_owner_grant(self) -> None:
        ledger = self.create()

        with self.assertRaises(LedgerNotFoundError):
            update_owned_ledger(
                self.databases.open_registry,
                self.other_user.uuid,
                ledger.uuid,
                "Stolen",
                "lucide:Wallet",
                b"\x00\x00\x00",
                120,
            )
        with self.assertRaises(LedgerNotFoundError):
            delete_owned_ledger(
                self.databases.open_registry,
                self.databases.delete_ledger_database,
                self.other_user.uuid,
                ledger.uuid,
            )

        self.assertEqual(get_owned_ledger(self.databases.open_registry, self.user.uuid, ledger.uuid), ledger)
        self.assertTrue((self.databases.ledger_dbs_dir / ledger.path).is_file())

    def test_delete_removes_registry_grant_and_database(self) -> None:
        ledger = self.create()

        delete_owned_ledger(
            self.databases.open_registry,
            self.databases.delete_ledger_database,
            self.user.uuid,
            ledger.uuid,
        )

        with self.databases.open_registry() as unit_of_work:
            self.assertIsNone(unit_of_work.ledger_repository.get(ledger.uuid))
            self.assertEqual(unit_of_work.ledger_grant_repository.list_by_ledger(ledger.uuid), [])
        self.assertFalse((self.databases.ledger_dbs_dir / ledger.path).exists())


if __name__ == "__main__":
    unittest.main()
