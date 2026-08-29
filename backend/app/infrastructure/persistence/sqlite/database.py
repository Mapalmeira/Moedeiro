import sqlite3
from pathlib import Path
from typing import Self


class SqliteDatabase:
    def __init__(self, path: Path):
        self.path = path

    def get_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
        except Exception:
            connection.close()
            raise
        return connection

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
