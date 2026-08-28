"""Integration tests for the registry SQLite ledger-token repository."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pydantic import ValidationError

from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.registry.repository.ledger import SqliteLedgerRepository
from app.infrastructure.persistence.sqlite.registry.repository.ledger_token import SqliteLedgerTokenRepository


SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
)


class SqliteLedgerTokenRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "registry.sqlite"
        self.connection = SqliteDatabase(database_path).get_connection()
        self.connection.executescript(SCHEMA_PATH.read_text())
        self.ledger_repository = SqliteLedgerRepository(self.connection)
        self.repository = SqliteLedgerTokenRepository(self.connection)

        self.ledger_repository.create("ledger.sqlite")
        self.ledger = self.ledger_repository.get_by_path("ledger.sqlite")
        assert self.ledger is not None
        self.connection.commit()

    def tearDown(self) -> None:
        self.connection.close()
        self.temporary_directory.cleanup()

    def test_create_can_be_read_by_uuid_and_token_hash(self) -> None:
        """create persists generated identity and all supplied token fields."""
        self.repository.create(
            self.ledger.uuid,
            "token-hash",
            "personal",
            10,
        )

        token = self.repository.get_by_token_hash("token-hash")

        self.assertIsNotNone(token)
        assert token is not None
        self.assertEqual(self.repository.get(token.uuid), token)
        self.assertEqual(token.ledger_uuid, self.ledger.uuid)
        self.assertEqual(token.label, "personal")
        self.assertEqual(token.created_at, 10)
        self.assertIsNone(token.revoked_at)

    def test_get_returns_none_when_token_does_not_exist(self) -> None:
        """get_by_token_hash represents an absent token with None."""
        self.assertIsNone(self.repository.get_by_token_hash("unknown-hash"))

    def test_update_label_accepts_text_and_none(self) -> None:
        """A label can be changed and subsequently cleared."""
        self.repository.create(self.ledger.uuid, "token-hash", None, 10)
        token = self.repository.get_by_token_hash("token-hash")
        assert token is not None

        self.repository.update_label(token.uuid, "primary")
        updated_token = self.repository.get(token.uuid)
        assert updated_token is not None
        self.assertEqual(updated_token.label, "primary")

        self.repository.update_label(token.uuid, None)
        cleared_token = self.repository.get(token.uuid)
        assert cleared_token is not None
        self.assertIsNone(cleared_token.label)

    def test_update_label_rejects_text_longer_than_model_limit(self) -> None:
        """The 30-character label limit is enforced before executing the update."""
        self.repository.create(self.ledger.uuid, "token-hash", None, 10)
        token = self.repository.get_by_token_hash("token-hash")
        assert token is not None

        with self.assertRaises(ValidationError):
            self.repository.update_label(token.uuid, "x" * 31)

    def test_revoke_records_only_the_first_revocation_time(self) -> None:
        """Revoking an already revoked token does not overwrite its timestamp."""
        self.repository.create(self.ledger.uuid, "token-hash", None, 10)
        token = self.repository.get_by_token_hash("token-hash")
        assert token is not None

        self.repository.revoke(token.uuid, 30)
        self.repository.revoke(token.uuid, 40)

        revoked_token = self.repository.get(token.uuid)
        assert revoked_token is not None
        self.assertEqual(revoked_token.revoked_at, 30)

    def test_list_by_ledger_excludes_tokens_from_other_ledgers(self) -> None:
        """list_by_ledger applies the foreign-key filter correctly."""
        self.ledger_repository.create("other.sqlite")
        other_ledger = self.ledger_repository.get_by_path("other.sqlite")
        assert other_ledger is not None
        self.repository.create(self.ledger.uuid, "first-hash", None, 10)
        self.repository.create(self.ledger.uuid, "second-hash", None, 20)
        self.repository.create(other_ledger.uuid, "other-hash", None, 30)

        tokens = self.repository.list_by_ledger(self.ledger.uuid)

        self.assertCountEqual(
            [token.token_hash for token in tokens],
            ["first-hash", "second-hash"],
        )

    def test_list_all_returns_tokens_from_every_ledger(self) -> None:
        """list_all has no ledger filter and makes no ordering promise."""
        self.ledger_repository.create("other.sqlite")
        other_ledger = self.ledger_repository.get_by_path("other.sqlite")
        assert other_ledger is not None
        self.repository.create(self.ledger.uuid, "first-hash", None, 10)
        self.repository.create(other_ledger.uuid, "other-hash", None, 20)

        tokens = self.repository.list_all()

        self.assertCountEqual(
            [token.token_hash for token in tokens],
            ["first-hash", "other-hash"],
        )

    def test_list_page_applies_sort_direction_limit_and_offset(self) -> None:
        """Pagination uses the selected allowlisted column and requested direction."""
        self.repository.create(self.ledger.uuid, "charlie", None, 10)
        self.repository.create(self.ledger.uuid, "alpha", None, 20)
        self.repository.create(self.ledger.uuid, "bravo", None, 30)

        ascending_page = self.repository.list_page(2, 1, "token_hash", True)
        descending_page = self.repository.list_page(1, 2, "token_hash", False)

        self.assertEqual([token.token_hash for token in ascending_page], ["bravo"])
        self.assertEqual(
            [token.token_hash for token in descending_page],
            ["charlie", "bravo"],
        )

    def test_list_page_rejects_invalid_page_boundaries(self) -> None:
        """Page number and size must both be positive integers."""
        with self.subTest(page_number=0):
            with self.assertRaises(ValueError):
                self.repository.list_page(0, 10, "token_hash", True)

        with self.subTest(page_size=0):
            with self.assertRaises(ValueError):
                self.repository.list_page(1, 0, "token_hash", True)

    def test_list_page_rejects_uuid_sort_keys(self) -> None:
        """Neither entity UUID nor foreign-key UUID is a public sort option."""
        for sort_key in ("uuid", "ledger_uuid"):
            with self.subTest(sort_key=sort_key):
                with self.assertRaises(ValueError):
                    self.repository.list_page(1, 10, sort_key, True)

    def test_list_page_rejects_unknown_sort_keys(self) -> None:
        """The sort-key allowlist prevents arbitrary SQL fragments."""
        with self.assertRaises(ValueError):
            self.repository.list_page(
                1,
                10,
                "DROP TABLE ledger_token",
                True,
            )

    def test_create_rejects_text_longer_than_model_limits(self) -> None:
        """Token hash and label limits are enforced before insertion."""
        with self.subTest(field="token_hash"):
            with self.assertRaises(ValidationError):
                self.repository.create(self.ledger.uuid, "x" * 256, None, 10)

        with self.subTest(field="label"):
            with self.assertRaises(ValidationError):
                self.repository.create(self.ledger.uuid, "token-hash", "x" * 31, 10)

    def test_repository_does_not_commit_its_own_changes(self) -> None:
        """Transaction ownership remains with the unit of work."""
        self.repository.create(self.ledger.uuid, "token-hash", None, 10)

        self.connection.rollback()

        self.assertIsNone(self.repository.get_by_token_hash("token-hash"))


if __name__ == "__main__":
    unittest.main()
