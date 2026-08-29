import sqlite3
from uuid import UUID, uuid4

from app.domain.registry.model.ledger import Ledger
from app.domain.registry.repository.ledger import LedgerRepository


class SqliteLedgerRepository(LedgerRepository):
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, path: str) -> Ledger:
        ledger = Ledger(uuid=uuid4(), path=path)
        self.connection.execute(
            "INSERT INTO ledger(uuid, path) VALUES (?, ?)",
            (ledger.uuid.bytes, ledger.path),
        )
        return ledger

    def get(self, uuid: UUID) -> Ledger | None:
        row = self.connection.execute(
            "SELECT uuid, path FROM ledger WHERE uuid = ?",
            (uuid.bytes,),
        ).fetchone()
        if row is None:
            return None
        return self._to_model(row)

    def get_by_path(self, path: str) -> Ledger | None:
        row = self.connection.execute(
            "SELECT uuid, path FROM ledger WHERE path = ?",
            (path,),
        ).fetchone()
        if row is None:
            return None
        return self._to_model(row)

    def update_path(self, uuid: UUID, value: str) -> None:
        ledger = Ledger(uuid=uuid, path=value)
        self.connection.execute(
            "UPDATE ledger SET path = ? WHERE uuid = ?",
            (ledger.path, ledger.uuid.bytes),
        )

    def delete(self, uuid: UUID) -> None:
        self.connection.execute(
            "DELETE FROM ledger WHERE uuid = ?",
            (uuid.bytes,),
        )

    def list_all(self) -> list[Ledger]:
        rows = self.connection.execute(
            "SELECT uuid, path FROM ledger"
        ).fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: sqlite3.Row) -> Ledger:
        return Ledger.model_validate(dict(row))
