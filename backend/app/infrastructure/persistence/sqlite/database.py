from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
import sqlite3

from app.infrastructure.persistence.database import Database

class SqliteDatabase(Database[sqlite3.Connection]):
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)

        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
        finally:
            conn.close()
