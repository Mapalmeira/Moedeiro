from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.ledger.schema_version import CURRENT_LEDGER_SCHEMA_VERSION
from app.infrastructure.persistence.sqlite.migration import SqliteSchemaMigrator


MIGRATIONS_DIRECTORY = Path(__file__).resolve().parents[3] / "app/infrastructure/persistence/sqlite/ledger/schema/migrations"


class LedgerSpecialTypeMigrationTest(unittest.TestCase):
    def test_v2_adds_special_type_and_marks_legacy_transfer_fees(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.sqlite"
            connection = sqlite3.connect(path)
            try:
                connection.executescript(
                    """
                    CREATE TABLE ledger_metadata (
                        singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                        schema_version INTEGER NOT NULL CHECK (schema_version >= 1)
                    ) STRICT;
                    CREATE TABLE financial_event (
                        uuid BLOB PRIMARY KEY,
                        occurred_at INTEGER NOT NULL,
                        description TEXT NOT NULL,
                        type TEXT NOT NULL
                    ) STRICT;
                    CREATE TABLE financial_movement (
                        uuid BLOB PRIMARY KEY,
                        financial_event_uuid BLOB NOT NULL,
                        value INTEGER NOT NULL,
                        quantity INTEGER NOT NULL DEFAULT 1,
                        item_name TEXT,
                        account_uuid BLOB NOT NULL,
                        category_uuid BLOB NOT NULL
                    ) STRICT;
                    INSERT INTO ledger_metadata(singleton, schema_version) VALUES (1, 1);
                    """
                )
                transfer_uuid = uuid4().bytes
                transaction_uuid = uuid4().bytes
                source_account = uuid4().bytes
                destination_account = uuid4().bytes
                category = uuid4().bytes
                connection.execute("INSERT INTO financial_event VALUES (?, 10, 'Transfer', 'ACCOUNT_TRANSFER')", (transfer_uuid,))
                connection.execute("INSERT INTO financial_event VALUES (?, 11, 'Expense', 'TRANSACTION')", (transaction_uuid,))
                source_movement_uuid = uuid4().bytes
                destination_movement_uuid = uuid4().bytes
                connection.execute("INSERT INTO financial_movement VALUES (?, ?, -100, 1, NULL, ?, ?)", (source_movement_uuid, transfer_uuid, source_account, category))
                connection.execute("INSERT INTO financial_movement VALUES (?, ?, 100, 1, NULL, ?, ?)", (destination_movement_uuid, transfer_uuid, destination_account, category))
                fee_uuid = uuid4().bytes
                connection.execute("INSERT INTO financial_movement VALUES (?, ?, -5, 1, NULL, ?, ?)", (fee_uuid, transfer_uuid, destination_account, category))
                transaction_movement_uuid = uuid4().bytes
                connection.execute("INSERT INTO financial_movement VALUES (?, ?, -10, 1, NULL, ?, ?)", (transaction_movement_uuid, transaction_uuid, destination_account, category))
                connection.commit()
            finally:
                connection.close()

            migrator = SqliteSchemaMigrator("ledger_metadata", CURRENT_LEDGER_SCHEMA_VERSION, MIGRATIONS_DIRECTORY)
            self.assertEqual(migrator.migrate(SqliteDatabase(path)), 1)

            connection = sqlite3.connect(path)
            try:
                self.assertIn("special_type", {row[1] for row in connection.execute("PRAGMA table_info(financial_movement)")})
                self.assertEqual(connection.execute("SELECT special_type FROM financial_movement WHERE uuid = ?", (fee_uuid,)).fetchone()[0], "FEE")
                self.assertIsNone(connection.execute("SELECT special_type FROM financial_movement WHERE uuid = ?", (source_movement_uuid,)).fetchone()[0])
                self.assertIsNone(connection.execute("SELECT special_type FROM financial_movement WHERE uuid = ?", (destination_movement_uuid,)).fetchone()[0])
                self.assertIsNone(connection.execute("SELECT special_type FROM financial_movement WHERE uuid = ?", (transaction_movement_uuid,)).fetchone()[0])
                self.assertEqual(connection.execute("SELECT schema_version FROM ledger_metadata WHERE singleton = 1").fetchone()[0], 2)
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute("UPDATE financial_movement SET special_type = 'OTHER' WHERE uuid = ?", (fee_uuid,))
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
