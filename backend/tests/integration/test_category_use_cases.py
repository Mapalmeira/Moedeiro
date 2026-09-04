from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

from pydantic import ValidationError

from app.application.ledger.exceptions import CategoryInUseError, CategoryNotFoundError, CategoryTreeSizeExceededError, InvalidCategoryHierarchyError
from app.application.ledger.use_cases.category import create_category, delete_category, get_category, get_category_tree, update_category
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.ledger.unit_of_work import SqliteLedgerUnitOfWork


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class CategoryUseCasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.database = SqliteDatabase.initialize(Path(self.temporary_directory.name) / "ledger.sqlite", SCHEMA_PATH)
        with self.open_ledger() as unit_of_work:
            unit_of_work.ledger_metadata_repository.create(uuid4(), 1, 10)
            self.currency = unit_of_work.currency_repository.create("Real", "R$", None, 2, "CircleDollarSign", b"\x10\x20\x30")
            self.account = unit_of_work.account_repository.create("Checking", None, self.currency.uuid, "WalletCards", b"\x40\x50\x60")
            unit_of_work.commit()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def open_ledger(self) -> SqliteLedgerUnitOfWork:
        return SqliteLedgerUnitOfWork(self.database)

    def create(self, name: str = "Food", parent_uuid=None):
        return create_category(self.open_ledger, name, "Utensils", b"\x70\x80\x90", parent_uuid)

    def test_create_commits_and_returns_a_root_or_child_category(self) -> None:
        parent = self.create("Food")
        child = self.create("Restaurants", parent.uuid)

        self.assertEqual(get_category(self.open_ledger, parent.uuid), parent)
        self.assertEqual(get_category(self.open_ledger, child.uuid), child)

    def test_create_rejects_an_unknown_parent_or_invalid_data(self) -> None:
        with self.assertRaises(CategoryNotFoundError):
            self.create("Child", uuid4())
        with self.assertRaises(ValidationError):
            self.create("")

        self.assertEqual(get_category_tree(self.open_ledger), [])

    def test_get_raises_for_an_unknown_category(self) -> None:
        with self.assertRaises(CategoryNotFoundError):
            get_category(self.open_ledger, uuid4())

    def test_get_tree_returns_the_complete_hierarchy(self) -> None:
        parent = self.create("Food")
        child = self.create("Restaurants", parent.uuid)

        tree = get_category_tree(self.open_ledger)

        self.assertEqual(len(tree), 1)
        self.assertEqual(tree[0].category, parent)
        self.assertEqual(tree[0].children[0].category, child)

    def test_create_and_tree_read_enforce_the_domain_category_limit(self) -> None:
        self.create("First")
        self.create("Second")

        with patch("app.application.ledger.use_cases.category.MAX_CATEGORY_TREE_SIZE", 2):
            with self.assertRaises(CategoryTreeSizeExceededError):
                self.create("Third")

        with patch("app.application.ledger.use_cases.category.MAX_CATEGORY_TREE_SIZE", 1):
            with self.assertRaises(CategoryTreeSizeExceededError):
                get_category_tree(self.open_ledger)

    def test_update_changes_all_mutable_fields_and_parent(self) -> None:
        parent = self.create("Parent")
        category = self.create("Old")

        updated = update_category(self.open_ledger, category.uuid, "New", "Shapes", b"\xaa\xbb\xcc", parent.uuid)

        self.assertEqual(updated.name, "New")
        self.assertEqual(updated.icon, "Shapes")
        self.assertEqual(updated.color_code, b"\xaa\xbb\xcc")
        self.assertEqual(updated.parent_uuid, parent.uuid)
        self.assertEqual(get_category(self.open_ledger, category.uuid), updated)

    def test_update_rejects_an_unknown_category_or_parent(self) -> None:
        category = self.create()

        with self.assertRaises(CategoryNotFoundError):
            update_category(self.open_ledger, uuid4(), "Missing", "Circle", b"\x10\x20\x30", None)
        with self.assertRaises(CategoryNotFoundError):
            update_category(self.open_ledger, category.uuid, "Child", "Circle", b"\x10\x20\x30", uuid4())

        self.assertEqual(get_category(self.open_ledger, category.uuid), category)

    def test_update_rejects_a_parent_cycle_without_persisting_partial_changes(self) -> None:
        parent = self.create("Parent")
        child = self.create("Child", parent.uuid)

        with self.assertRaises(InvalidCategoryHierarchyError):
            update_category(self.open_ledger, parent.uuid, "Changed", "Shapes", b"\xaa\xbb\xcc", child.uuid)

        self.assertEqual(get_category(self.open_ledger, parent.uuid), parent)

    def test_delete_removes_an_unused_subtree(self) -> None:
        parent = self.create("Parent")
        child = self.create("Child", parent.uuid)

        self.assertIsNone(delete_category(self.open_ledger, parent.uuid))

        for category_uuid in (parent.uuid, child.uuid):
            with self.subTest(category_uuid=category_uuid):
                with self.assertRaises(CategoryNotFoundError):
                    get_category(self.open_ledger, category_uuid)

    def test_delete_rejects_a_category_with_a_used_descendant(self) -> None:
        parent = self.create("Parent")
        child = self.create("Child", parent.uuid)
        with self.open_ledger() as unit_of_work:
            event = unit_of_work.financial_event_repository.create(20, "Purchase", "TRANSACTION")
            unit_of_work.financial_movement_repository.create(event.uuid, self.account.uuid, child.uuid, -100, None)
            unit_of_work.commit()

        with self.assertRaises(CategoryInUseError):
            delete_category(self.open_ledger, parent.uuid)

        self.assertEqual(get_category(self.open_ledger, parent.uuid), parent)
        self.assertEqual(get_category(self.open_ledger, child.uuid), child)

    def test_delete_rejects_an_unknown_category(self) -> None:
        with self.assertRaises(CategoryNotFoundError):
            delete_category(self.open_ledger, uuid4())


if __name__ == "__main__":
    unittest.main()
