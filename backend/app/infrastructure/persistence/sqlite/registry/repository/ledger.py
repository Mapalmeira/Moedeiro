import sqlite3
from uuid import UUID, uuid4

from pydantic import TypeAdapter

from app.domain.appearance import Icon, RgbColorCode
from app.domain.registry.model.ledger import Ledger, LedgerName
from app.domain.registry.repository.ledger import LedgerRepository


class SqliteLedgerRepository(LedgerRepository):
    _name_adapter = TypeAdapter(LedgerName)
    _icon_adapter = TypeAdapter(Icon)
    _color_code_adapter = TypeAdapter(RgbColorCode)

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, name: str, path: str, icon: str, color_code: bytes) -> Ledger:
        ledger = Ledger(uuid=uuid4(), name=name, path=path, icon=icon, color_code=color_code)
        self.connection.execute(
            "INSERT INTO ledger(uuid, name, path, icon, color_code) VALUES (?, ?, ?, ?, ?)",
            (ledger.uuid.bytes, ledger.name, ledger.path, ledger.icon, ledger.color_code),
        )
        return ledger

    def get(self, uuid: UUID) -> Ledger | None:
        row = self.connection.execute(
            "SELECT uuid, name, path, icon, color_code FROM ledger WHERE uuid = ?",
            (uuid.bytes,),
        ).fetchone()
        if row is None:
            return None
        return self._to_model(row)

    def get_by_path(self, path: str) -> Ledger | None:
        row = self.connection.execute(
            "SELECT uuid, name, path, icon, color_code FROM ledger WHERE path = ?",
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

    def update_name(self, uuid: UUID, value: str) -> None:
        name = self._name_adapter.validate_python(value)
        self.connection.execute(
            "UPDATE ledger SET name = ? WHERE uuid = ?",
            (name, uuid.bytes),
        )

    def update_icon(self, uuid: UUID, value: str) -> None:
        icon = self._icon_adapter.validate_python(value)
        self.connection.execute(
            "UPDATE ledger SET icon = ? WHERE uuid = ?",
            (icon, uuid.bytes),
        )

    def update_color_code(self, uuid: UUID, value: bytes) -> None:
        color_code = self._color_code_adapter.validate_python(value)
        self.connection.execute(
            "UPDATE ledger SET color_code = ? WHERE uuid = ?",
            (color_code, uuid.bytes),
        )

    def delete(self, uuid: UUID) -> None:
        self.connection.execute(
            "DELETE FROM ledger WHERE uuid = ?",
            (uuid.bytes,),
        )

    def list_all(self) -> list[Ledger]:
        rows = self.connection.execute(
            "SELECT uuid, name, path, icon, color_code FROM ledger"
        ).fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: sqlite3.Row) -> Ledger:
        return Ledger.model_validate(dict(row))
