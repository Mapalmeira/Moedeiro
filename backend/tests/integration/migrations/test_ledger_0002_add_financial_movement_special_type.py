from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.ledger.schema_version import CURRENT_LEDGER_SCHEMA_VERSION
from app.infrastructure.persistence.sqlite.migration import SqliteSchemaMigrator
from tests.integration.migrations.fixture import create_database_from_schema_fixture


MIGRATIONS_DIRECTORY = Path(__file__).resolve().parents[3] / "app/infrastructure/persistence/sqlite/ledger/schema/migrations"


class LedgerSpecialTypeMigrationTest(unittest.TestCase):
    def test_v2_adds_special_type_and_marks_legacy_transfer_fees(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.sqlite"
            create_database_from_schema_fixture("ledger_v1.sql", path)

            ledger_uuid = uuid4().bytes
            currency_uuid = uuid4().bytes
            source_account = uuid4().bytes
            destination_account = uuid4().bytes
            category = uuid4().bytes
            transfer_uuid = uuid4().bytes
            transaction_uuid = uuid4().bytes
            source_movement_uuid = uuid4().bytes
            destination_movement_uuid = uuid4().bytes
            fee_uuid = uuid4().bytes
            transaction_movement_uuid = uuid4().bytes

            connection = sqlite3.connect(path)
            try:
                connection.execute("PRAGMA foreign_keys = ON")
                connection.execute("INSERT INTO ledger_metadata VALUES (1, ?, 1, 0)", (ledger_uuid,))
                connection.execute(
                    "INSERT INTO currency VALUES (?, 'Dollar', '$', NULL, 2, 'lucide:DollarSign', ?)",
                    (currency_uuid, b"\x80\x80\x80"),
                )
                connection.execute(
                    "INSERT INTO account VALUES (?, 'Source', NULL, ?, 'lucide:Wallet', ?)",
                    (source_account, currency_uuid, b"\x80\x80\x80"),
                )
                connection.execute(
                    "INSERT INTO account VALUES (?, 'Destination', NULL, ?, 'lucide:Wallet', ?)",
                    (destination_account, currency_uuid, b"\x80\x80\x80"),
                )
                connection.execute(
                    "INSERT INTO category VALUES (?, 'Transfer', 'lucide:ArrowRightLeft', ?, NULL)",
                    (category, b"\x80\x80\x80"),
                )
                connection.execute(
                    "INSERT INTO financial_event VALUES (?, 10, 'Transfer', 'ACCOUNT_TRANSFER')",
                    (transfer_uuid,),
                )
                connection.execute(
                    "INSERT INTO financial_event VALUES (?, 11, 'Expense', 'TRANSACTION')",
                    (transaction_uuid,),
                )
                connection.execute(
                    "INSERT INTO financial_movement VALUES (?, ?, -100, 1, NULL, ?, ?)",
                    (source_movement_uuid, transfer_uuid, source_account, category),
                )
                connection.execute(
                    "INSERT INTO financial_movement VALUES (?, ?, 100, 1, NULL, ?, ?)",
                    (destination_movement_uuid, transfer_uuid, destination_account, category),
                )
                connection.execute(
                    "INSERT INTO financial_movement VALUES (?, ?, -5, 1, NULL, ?, ?)",
                    (fee_uuid, transfer_uuid, destination_account, category),
                )
                connection.execute(
                    "INSERT INTO financial_movement VALUES (?, ?, -10, 1, NULL, ?, ?)",
                    (transaction_movement_uuid, transaction_uuid, destination_account, category),
                )
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
                self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute("UPDATE financial_movement SET special_type = 'OTHER' WHERE uuid = ?", (fee_uuid,))
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
