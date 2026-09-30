import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from app.infrastructure.persistence.sqlite.database import SqliteDatabase


class SqliteDatabaseErrorsTest(unittest.TestCase):
    def test_connection_is_closed_when_configuration_fails(self) -> None:
        connection = MagicMock()
        connection.execute.side_effect = RuntimeError("configuration failed")

        with patch("app.infrastructure.persistence.sqlite.database.sqlite3.connect", return_value=connection):
            with self.assertRaisesRegex(RuntimeError, "configuration failed"):
                SqliteDatabase(Path("database.sqlite")).get_connection()

        connection.close.assert_called_once_with()

    def test_enable_wal_rejects_an_unexpected_journal_mode_and_closes_connection(self) -> None:
        connection = MagicMock()
        connection.execute.return_value.fetchone.return_value = ("delete",)
        database = SqliteDatabase(Path("database.sqlite"))

        with patch.object(database, "get_connection", return_value=connection):
            with self.assertRaisesRegex(RuntimeError, "SQLite did not enable WAL mode: delete"):
                database.enable_wal()

        connection.close.assert_called_once_with()

    def test_failed_backup_closes_connections_and_removes_destination(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "backup/database.sqlite"
            destination.parent.mkdir()
            destination.write_bytes(b"partial")
            source = MagicMock()
            backup = MagicMock()
            source.backup.side_effect = sqlite3.OperationalError("backup failed")
            database = SqliteDatabase(Path(temporary_directory) / "source.sqlite")

            with patch.object(database, "get_connection", return_value=source), patch(
                "app.infrastructure.persistence.sqlite.database.sqlite3.connect", return_value=backup
            ):
                with self.assertRaisesRegex(sqlite3.OperationalError, "backup failed"):
                    database.backup_to(destination)

            self.assertFalse(destination.exists())
            backup.close.assert_called_once_with()
            source.close.assert_called_once_with()
