import sqlite3
from uuid import UUID

from pydantic import TypeAdapter

from app.domain.appearance import Icon, RgbColorCode
from app.domain.registry.model.ledger import Ledger, LedgerAccessTimestamp, LedgerName
from app.domain.registry.repository.ledger import LedgerRepository


class SqliteLedgerRepository(LedgerRepository):
    _SORT_COLUMNS = {
        "name": "ledger.name",
        "last_accessed_at": "ledger.last_accessed_at",
    }
    _name_adapter = TypeAdapter(LedgerName)
    _icon_adapter = TypeAdapter(Icon)
    _color_code_adapter = TypeAdapter(RgbColorCode)
    _last_accessed_at_adapter = TypeAdapter(LedgerAccessTimestamp)

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, uuid: UUID, name: LedgerName, path: str, icon: Icon, color_code: RgbColorCode, last_accessed_at: LedgerAccessTimestamp) -> Ledger:
        ledger = Ledger(uuid=uuid, name=name, path=path, icon=icon, color_code=color_code, last_accessed_at=last_accessed_at)
        self.connection.execute(
            "INSERT INTO ledger(uuid, name, path, icon, color_code, last_accessed_at) VALUES (?, ?, ?, ?, ?, ?)",
            (ledger.uuid.bytes, ledger.name, ledger.path, ledger.icon, ledger.color_code, ledger.last_accessed_at),
        )
        return ledger

    def get(self, uuid: UUID) -> Ledger | None:
        row = self.connection.execute(
            "SELECT uuid, name, path, icon, color_code, last_accessed_at FROM ledger WHERE uuid = ?",
            (uuid.bytes,),
        ).fetchone()
        if row is None:
            return None
        return self._to_model(row)

    def get_by_path(self, path: str) -> Ledger | None:
        row = self.connection.execute(
            "SELECT uuid, name, path, icon, color_code, last_accessed_at FROM ledger WHERE path = ?",
            (path,),
        ).fetchone()
        if row is None:
            return None
        return self._to_model(row)

    def update_path(self, uuid: UUID, value: str) -> None:
        self.connection.execute(
            "UPDATE ledger SET path = ? WHERE uuid = ?",
            (value, uuid.bytes),
        )

    def update_name(self, uuid: UUID, value: LedgerName) -> None:
        name = self._name_adapter.validate_python(value)
        self.connection.execute(
            "UPDATE ledger SET name = ? WHERE uuid = ?",
            (name, uuid.bytes),
        )

    def update_icon(self, uuid: UUID, value: Icon) -> None:
        icon = self._icon_adapter.validate_python(value)
        self.connection.execute(
            "UPDATE ledger SET icon = ? WHERE uuid = ?",
            (icon, uuid.bytes),
        )

    def update_color_code(self, uuid: UUID, value: RgbColorCode) -> None:
        color_code = self._color_code_adapter.validate_python(value)
        self.connection.execute(
            "UPDATE ledger SET color_code = ? WHERE uuid = ?",
            (color_code, uuid.bytes),
        )

    def update_last_accessed_at(self, uuid: UUID, value: LedgerAccessTimestamp) -> None:
        last_accessed_at = self._last_accessed_at_adapter.validate_python(value)
        self.connection.execute(
            "UPDATE ledger SET last_accessed_at = ? WHERE uuid = ? AND last_accessed_at < ?",
            (last_accessed_at, uuid.bytes, last_accessed_at),
        )

    def delete(self, uuid: UUID) -> None:
        self.connection.execute(
            "DELETE FROM ledger WHERE uuid = ?",
            (uuid.bytes,),
        )

    def list_all(self, sort_key: str, ascending: bool) -> list[Ledger]:
        sort_column = self._get_sort_column(sort_key)
        direction = "ASC" if ascending else "DESC"
        rows = self.connection.execute(
            f"SELECT uuid, name, path, icon, color_code, last_accessed_at FROM ledger ORDER BY {sort_column} {direction}, ledger.uuid ASC"
        ).fetchall()
        return [self._to_model(row) for row in rows]

    def list_owned_by_user(self, user_uuid: UUID, sort_key: str, ascending: bool) -> list[Ledger]:
        sort_column = self._get_sort_column(sort_key)
        direction = "ASC" if ascending else "DESC"
        rows = self.connection.execute(
            f"""
            SELECT ledger.uuid, ledger.name, ledger.path, ledger.icon, ledger.color_code, ledger.last_accessed_at
            FROM ledger
            JOIN ledger_grant ON ledger_grant.ledger_uuid = ledger.uuid
            WHERE ledger_grant.user_uuid = ?
              AND ledger_grant.type = 'OWNER'
              AND ledger_grant.revoked_at IS NULL
            ORDER BY {sort_column} {direction}, ledger.uuid ASC
            """,
            (user_uuid.bytes,),
        ).fetchall()
        return [self._to_model(row) for row in rows]

    def count_owned_by_user(self, user_uuid: UUID) -> int:
        return int(
            self.connection.execute(
                """
                SELECT COUNT(*)
                FROM ledger
                JOIN ledger_grant ON ledger_grant.ledger_uuid = ledger.uuid
                WHERE ledger_grant.user_uuid = ?
                  AND ledger_grant.type = 'OWNER'
                  AND ledger_grant.revoked_at IS NULL
                """,
                (user_uuid.bytes,),
            ).fetchone()[0]
        )

    @staticmethod
    def _to_model(row: sqlite3.Row) -> Ledger:
        return Ledger.model_validate(dict(row))

    @classmethod
    def _get_sort_column(cls, sort_key: str) -> str:
        try:
            return cls._SORT_COLUMNS[sort_key]
        except KeyError as error:
            raise ValueError(f"Invalid ledger sort key: {sort_key}") from error
