import sqlite3
from pathlib import Path


class SqliteDatabase:
    def __init__(self, path: Path):
        self.path = path

    def get_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
