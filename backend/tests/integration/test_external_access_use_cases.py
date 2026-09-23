import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from app.application.registry.exceptions import ExternalAccessNotFoundError
from app.application.registry.use_cases.external_access import delete_external_access, list_external_accesses
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.registry.unit_of_work import SqliteRegistryUnitOfWork


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"


class ExternalAccessUseCasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.database = SqliteDatabase.initialize(Path(self.temporary_directory.name) / "registry.sqlite", SCHEMA_PATH)
        with self.open_registry() as unit_of_work:
            self.first = unit_of_work.external_access_repository.create("First", b"a" * 32)
            self.second = unit_of_work.external_access_repository.create("Second", b"b" * 32)
            unit_of_work.commit()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def open_registry(self) -> SqliteRegistryUnitOfWork:
        return SqliteRegistryUnitOfWork(self.database)

    def test_list_returns_all_external_accesses(self) -> None:
        self.assertEqual(list_external_accesses(self.open_registry), [self.first, self.second])

    def test_delete_removes_external_access_and_its_grants(self) -> None:
        with self.open_registry() as unit_of_work:
            ledger = unit_of_work.ledger_repository.create(uuid4(), "Ledger", "ledger.sqlite", "lucide:BookOpen", b"\x80\x80\x80", 10)
            grant = unit_of_work.ledger_grant_repository.create(self.first.uuid, ledger.uuid, "GUEST", 20)
            unit_of_work.commit()

        delete_external_access(self.open_registry, self.first.uuid)

        with self.open_registry() as unit_of_work:
            self.assertIsNone(unit_of_work.external_access_repository.get(self.first.uuid))
            self.assertIsNone(unit_of_work.ledger_grant_repository.get(grant.uuid))

    def test_delete_rejects_missing_access(self) -> None:
        with self.assertRaises(ExternalAccessNotFoundError):
            delete_external_access(self.open_registry, uuid4())
