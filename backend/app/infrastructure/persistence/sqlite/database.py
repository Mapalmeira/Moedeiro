import sqlite3
from pathlib import Path
from typing import Self

from app.infrastructure.persistence.sqlite.search import normalize_search


class SqliteDatabase:
    def __init__(self, path: Path):
        self.path = path

    def get_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.create_function("normalize_search", 1, normalize_search, deterministic=True)
        except Exception:
            connection.close()
            raise
        return connection

    def enable_wal(self) -> None:
        connection = self.get_connection()
        try:
            mode = connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]
            if mode.lower() != "wal":
                raise RuntimeError(f"SQLite did not enable WAL mode: {mode}")
        finally:
            connection.close()

    def backup_to(self, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        source = self.get_connection()
        try:
            backup = sqlite3.connect(destination)
            try:
                source.backup(backup)
            finally:
                backup.close()
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        finally:
            source.close()

    @classmethod
    def initialize(cls, path: Path, schema_path: Path) -> Self:
        database = cls(path)
        database.path.parent.mkdir(parents=True, exist_ok=True)
        database.path.touch(exist_ok=False)
        try:
            connection = database.get_connection()
            try:
                connection.executescript(schema_path.read_text(encoding="utf-8"))
                connection.commit()
            finally:
                connection.close()
        except Exception:
            database.path.unlink(missing_ok=True)
            raise
        return database
