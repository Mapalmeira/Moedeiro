from pathlib import Path
import sqlite3

class SqliteDatabase:
    def __init__(self, path: Path):
        self.path = path

    def get_connection(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn