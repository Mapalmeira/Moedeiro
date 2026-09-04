"""Applies schema changes and their version update in the same SQLite transaction."""

import sqlite3
from pathlib import Path

from app.infrastructure.persistence.sqlite.database import SqliteDatabase


class SchemaVersionError(RuntimeError):
    pass


class SqliteSchemaMigrator:
    def __init__(self, metadata_table: str, current_version: int, migrations_directory: Path):
        self.metadata_table = metadata_table
        self.current_version = current_version
        self.migrations_directory = migrations_directory

    def validate(self, database: SqliteDatabase) -> None:
        if self.requires_migration(database):
            raise SchemaVersionError(
                f"{database.path} uses an older schema version than {self.current_version}"
            )

    def requires_migration(self, database: SqliteDatabase) -> bool:
        version = self._get_version(database)
        if version > self.current_version:
            raise SchemaVersionError(
                f"{database.path} uses schema version {version}, but this release only supports up to {self.current_version}"
            )
        return version < self.current_version

    def migrate(self, database: SqliteDatabase) -> int:
        connection = database.get_connection()
        try:
            version = self._get_version_from_connection(connection, database.path)
            if version > self.current_version:
                raise SchemaVersionError(
                    f"{database.path} uses schema version {version}, but this release only supports up to {self.current_version}"
                )
            applied = 0
            for target_version in range(version + 1, self.current_version + 1):
                self._apply(connection, database.path, target_version)
                applied += 1
            return applied
        finally:
            connection.close()

    def _get_version(self, database: SqliteDatabase) -> int:
        connection = database.get_connection()
        try:
            return self._get_version_from_connection(connection, database.path)
        finally:
            connection.close()

    def _get_version_from_connection(self, connection: sqlite3.Connection, database_path: Path) -> int:
        try:
            row = connection.execute(
                f"SELECT schema_version FROM {self.metadata_table} WHERE singleton = 1"
            ).fetchone()
        except sqlite3.OperationalError as error:
            raise SchemaVersionError(f"{database_path} has no valid schema metadata") from error
        if row is None:
            raise SchemaVersionError(f"{database_path} has no valid schema metadata")
        return row[0]

    def _apply(self, connection: sqlite3.Connection, database_path: Path, target_version: int) -> None:
        migration_path = self._get_migration_path(target_version)
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._execute_script(connection, migration_path.read_text(encoding="utf-8"))
            cursor = connection.execute(
                f"UPDATE {self.metadata_table} SET schema_version = ? WHERE singleton = 1 AND schema_version = ?",
                (target_version, target_version - 1),
            )
            if cursor.rowcount != 1:
                raise SchemaVersionError(f"{database_path} changed while it was being migrated")
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    def _get_migration_path(self, target_version: int) -> Path:
        matches = list(self.migrations_directory.glob(f"{target_version:04d}_*.sql"))
        if len(matches) != 1:
            raise SchemaVersionError(
                f"expected one migration to schema version {target_version} in {self.migrations_directory}"
            )
        return matches[0]

    @staticmethod
    def _execute_script(connection: sqlite3.Connection, script: str) -> None:
        statement = ""
        for line in script.splitlines(keepends=True):
            statement += line
            if sqlite3.complete_statement(statement):
                connection.execute(statement)
                statement = ""
        if statement.strip():
            raise SchemaVersionError("migration contains an incomplete SQL statement")
