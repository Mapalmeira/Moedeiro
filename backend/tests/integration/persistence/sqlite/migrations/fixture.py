from pathlib import Path
import sqlite3


FIXTURES_DIRECTORY = Path(__file__).with_name("fixtures")


def create_database_from_schema_fixture(name: str, destination: Path) -> None:
    connection = sqlite3.connect(destination)
    try:
        connection.executescript((FIXTURES_DIRECTORY / name).read_text())
    finally:
        connection.close()
