from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException, Request
from pydantic import ValidationError

from app.api.ledger.routes.category import create_ledger_category, delete_ledger_category, get_ledger_category, get_ledger_category_tree, update_ledger_category
from app.api.registry.routes.ledger import create_owned_ledger
from app.api.ledger.schema.category import CreateCategoryRequest, UpdateCategoryRequest
from app.api.registry.schema.ledger import CreateLedgerRequest
from app.factory import create_app
from app.settings import Settings
from tests.fakes import FakeCredentialOperationExecutor, FakePasswordHasher, FakeRateLimiter, FakeTotpAuthenticator


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class CategoryRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        directory = Path(self.temporary_directory.name)
        self.application = create_app(
            Settings(
                registry_schema_path=REGISTRY_SCHEMA_PATH,
                ledger_schema_path=LEDGER_SCHEMA_PATH,
                registry_db_path=directory / "registry/registry.sqlite",
                ledger_dbs_dir=directory / "ledgers",
            ),
            FakePasswordHasher(),
            FakeRateLimiter(),
            FakeTotpAuthenticator(),
            FakeCredentialOperationExecutor(),
            mount_frontend=False,
        )
        with self.application.state.databases.open_registry() as unit_of_work:
            self.user = unit_of_work.user_repository.create("Alice", "$argon2id$test", 10)
            self.other_user = unit_of_work.user_repository.create("Bob", "$argon2id$test", 10)
            unit_of_work.commit()
        self.request = Request({"type": "http", "app": self.application, "client": ("192.0.2.1", 50000), "headers": []})
        self.ledger = create_owned_ledger(CreateLedgerRequest(name="Household", icon="lucide:WalletCards", color_code="#102030"), self.request, self.user)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def create_category(self, name: str = "Food", parent_uuid=None):
        return create_ledger_category(
            self.ledger.uuid,
            CreateCategoryRequest(name=name, icon="lucide:Utensils", color_code="#708090", parent_uuid=parent_uuid),
            self.request,
            self.user,
        )

    def test_create_get_and_tree_return_the_persisted_hierarchy(self) -> None:
        parent = self.create_category("Food")
        child = self.create_category("Restaurants", parent.uuid)

        self.assertEqual(get_ledger_category(self.ledger.uuid, child.uuid, self.request, self.user), child)
        tree = get_ledger_category_tree(self.ledger.uuid, self.request, self.user)
        self.assertEqual(len(tree), 1)
        self.assertEqual(tree[0].category, parent)
        self.assertEqual(tree[0].children[0].category, child)

    def test_create_and_update_reject_an_unknown_parent(self) -> None:
        category = self.create_category()

        with self.assertRaises(HTTPException) as create_error:
            self.create_category("Child", uuid4())
        with self.assertRaises(HTTPException) as update_error:
            update_ledger_category(
                self.ledger.uuid,
                category.uuid,
                UpdateCategoryRequest(name="Child", icon="lucide:Circle", color_code="#102030", parent_uuid=uuid4()),
                self.request,
                self.user,
            )

        self.assertEqual(create_error.exception.status_code, 404)
        self.assertEqual(update_error.exception.status_code, 404)

    def test_create_and_update_return_conflict_for_a_duplicate_name(self) -> None:
        first = self.create_category("Food")
        second = self.create_category("Transport")

        with self.assertRaises(HTTPException) as create_error:
            self.create_category(first.name)
        with self.assertRaises(HTTPException) as update_error:
            update_ledger_category(
                self.ledger.uuid,
                second.uuid,
                UpdateCategoryRequest(name=first.name, icon=second.icon, color_code=second.color_code),
                self.request,
                self.user,
            )

        for error in (create_error.exception, update_error.exception):
            self.assertEqual(error.status_code, 409)
            self.assertEqual(error.detail, "Category name unavailable")

    def test_create_returns_a_fixed_error_when_the_category_limit_is_reached(self) -> None:
        with patch("app.application.ledger.use_cases.category.MAX_CATEGORY_TREE_SIZE", 2):
            self.create_category("First")
            self.create_category("Second")
            with self.assertRaises(HTTPException) as raised:
                self.create_category("Third")

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, "Category limit exceeded")


    def test_create_returns_specific_conflict_for_depth_limit(self) -> None:
        parent = None
        for level in range(5):
            parent = self.create_category(f"Level {level}", None if parent is None else parent.uuid)

        with self.assertRaises(HTTPException) as raised:
            self.create_category("Too deep", parent.uuid)

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, "Category depth limit exceeded")

    def test_update_changes_category_data_and_parent(self) -> None:
        parent = self.create_category("Parent")
        category = self.create_category("Old")

        updated = update_ledger_category(
            self.ledger.uuid,
            category.uuid,
            UpdateCategoryRequest(name="New", icon="lucide:Shapes", color_code="#AABBCC", parent_uuid=parent.uuid),
            self.request,
            self.user,
        )

        self.assertEqual(updated.name, "New")
        self.assertEqual(updated.icon, "lucide:Shapes")
        self.assertEqual(updated.color_code, "#AABBCC")
        self.assertEqual(updated.parent_uuid, parent.uuid)

    def test_update_returns_conflict_for_a_parent_cycle(self) -> None:
        parent = self.create_category("Parent")
        child = self.create_category("Child", parent.uuid)

        with self.assertRaises(HTTPException) as raised:
            update_ledger_category(
                self.ledger.uuid,
                parent.uuid,
                UpdateCategoryRequest(name="Parent", icon="lucide:Circle", color_code="#102030", parent_uuid=child.uuid),
                self.request,
                self.user,
            )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, "Invalid category hierarchy")


    def test_update_returns_specific_conflict_for_depth_limit(self) -> None:
        first = self.create_category("First")
        second = self.create_category("Second", first.uuid)
        third = self.create_category("Third", second.uuid)
        fourth = self.create_category("Fourth", third.uuid)
        source = self.create_category("Source")
        self.create_category("Child", source.uuid)

        with self.assertRaises(HTTPException) as raised:
            update_ledger_category(
                self.ledger.uuid,
                source.uuid,
                UpdateCategoryRequest(name="Source", icon="lucide:Circle", color_code="#102030", parent_uuid=fourth.uuid),
                self.request,
                self.user,
            )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, "Category depth limit exceeded")

    def test_delete_removes_an_unused_category_subtree(self) -> None:
        parent = self.create_category("Parent")
        child = self.create_category("Child", parent.uuid)

        self.assertIsNone(delete_ledger_category(self.ledger.uuid, parent.uuid, self.request, self.user))

        for category_uuid in (parent.uuid, child.uuid):
            with self.subTest(category_uuid=category_uuid):
                with self.assertRaises(HTTPException) as raised:
                    get_ledger_category(self.ledger.uuid, category_uuid, self.request, self.user)
                self.assertEqual(raised.exception.status_code, 404)

    def test_delete_returns_conflict_when_a_descendant_is_in_use(self) -> None:
        parent = self.create_category("Parent")
        child = self.create_category("Child", parent.uuid)
        with self.application.state.databases.open_ledger(f"{self.ledger.uuid}.sqlite") as unit_of_work:
            currency = unit_of_work.currency_repository.create("Real", "R$", None, 2, "lucide:CircleDollarSign", b"\x10\x20\x30")
            account = unit_of_work.account_repository.create("Checking", None, currency.uuid, "lucide:WalletCards", b"\x40\x50\x60")
            event = unit_of_work.financial_event_repository.create(20, "Purchase", "TRANSACTION")
            unit_of_work.financial_movement_repository.create(event.uuid, account.uuid, child.uuid, -100, None)
            unit_of_work.commit()

        with self.assertRaises(HTTPException) as raised:
            delete_ledger_category(self.ledger.uuid, parent.uuid, self.request, self.user)

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, "Category is in use")

    def test_missing_category_returns_not_found(self) -> None:
        missing_uuid = uuid4()

        for operation in (
            lambda: get_ledger_category(self.ledger.uuid, missing_uuid, self.request, self.user),
            lambda: update_ledger_category(
                self.ledger.uuid,
                missing_uuid,
                UpdateCategoryRequest(name="Missing", icon="lucide:Circle", color_code="#102030"),
                self.request,
                self.user,
            ),
            lambda: delete_ledger_category(self.ledger.uuid, missing_uuid, self.request, self.user),
        ):
            with self.subTest(operation=operation):
                with self.assertRaises(HTTPException) as raised:
                    operation()
                self.assertEqual(raised.exception.status_code, 404)
                self.assertEqual(raised.exception.detail, "Category not found")

    def test_another_user_cannot_discover_or_change_categories(self) -> None:
        category = self.create_category()
        operations = (
            lambda: get_ledger_category_tree(self.ledger.uuid, self.request, self.other_user),
            lambda: get_ledger_category(self.ledger.uuid, category.uuid, self.request, self.other_user),
            lambda: update_ledger_category(
                self.ledger.uuid,
                category.uuid,
                UpdateCategoryRequest(name="Changed", icon="lucide:Circle", color_code="#102030"),
                self.request,
                self.other_user,
            ),
            lambda: delete_ledger_category(self.ledger.uuid, category.uuid, self.request, self.other_user),
        )

        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaises(HTTPException) as raised:
                    operation()
                self.assertEqual(raised.exception.status_code, 404)
                self.assertEqual(raised.exception.detail, "Ledger not found")

    def test_request_schemas_enforce_category_limits(self) -> None:
        invalid_values = (
            {"name": "", "icon": "lucide:Circle", "color_code": "#102030"},
            {"name": "x" * 31, "icon": "lucide:Circle", "color_code": "#102030"},
            {"name": "Food", "icon": "", "color_code": "#102030"},
            {"name": "Food", "icon": "Circle", "color_code": "#102030"},
            {"name": "Food", "icon": "lucide:Circle", "color_code": "red"},
        )
        for values in invalid_values:
            with self.subTest(values=values):
                with self.assertRaises(ValidationError):
                    CreateCategoryRequest(**values)

    def test_routes_expose_the_complete_category_lifecycle(self) -> None:
        paths = self.application.openapi()["paths"]
        collection = paths["/api/ledgers/{ledger_uuid}/categories"]
        tree = paths["/api/ledgers/{ledger_uuid}/categories/tree"]
        member = paths["/api/ledgers/{ledger_uuid}/categories/{category_uuid}"]

        self.assertIn("201", collection["post"]["responses"])
        self.assertNotIn("get", collection)
        self.assertIn("200", tree["get"]["responses"])
        self.assertIn("200", member["get"]["responses"])
        self.assertIn("200", member["put"]["responses"])
        self.assertNotIn("content", member["delete"]["responses"]["204"])


if __name__ == "__main__":
    unittest.main()
