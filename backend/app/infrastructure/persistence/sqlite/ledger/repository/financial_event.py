import sqlite3
from uuid import UUID, uuid4

from app.domain.ledger.model.financial_event import FinancialEvent, FinancialEventType
from app.domain.ledger.model.financial_event_filter import FinancialEventFilter
from app.domain.ledger.model.financial_movement import FinancialMovement
from app.domain.ledger.repository.financial_event import FinancialEventRepository
from app.infrastructure.persistence.sqlite.ledger.repository._financial_event_filter import build_financial_event_filter


class SqliteFinancialEventRepository(FinancialEventRepository):
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, occurred_at: int, description: str, type: FinancialEventType) -> FinancialEvent:
        event = FinancialEvent(uuid=uuid4(), occurred_at=occurred_at, description=description, type=type, movements=[])
        self.connection.execute(
            "INSERT INTO financial_event(uuid, occurred_at, description, type) VALUES (?, ?, ?, ?)",
            (event.uuid.bytes, event.occurred_at, event.description, event.type),
        )
        return event

    def get(self, uuid: UUID) -> FinancialEvent | None:
        row = self.connection.execute(
            "SELECT uuid, occurred_at, description, type FROM financial_event WHERE uuid = ?",
            (uuid.bytes,),
        ).fetchone()
        if row is None:
            return None
        return self._to_models([row])[0]

    def update_occurred_at(self, uuid: UUID, value: int) -> None:
        event = FinancialEvent(uuid=uuid, occurred_at=value, description="event", type="TRANSACTION", movements=[])
        self.connection.execute(
            "UPDATE financial_event SET occurred_at = ? WHERE uuid = ?",
            (event.occurred_at, event.uuid.bytes),
        )

    def update_description(self, uuid: UUID, value: str) -> None:
        event = FinancialEvent(uuid=uuid, occurred_at=0, description=value, type="TRANSACTION", movements=[])
        self.connection.execute(
            "UPDATE financial_event SET description = ? WHERE uuid = ?",
            (event.description, event.uuid.bytes),
        )

    def list_after(
        self,
        page_size: int,
        ascending: bool,
        filters: FinancialEventFilter,
        occurred_at: int | None,
        uuid: UUID | None,
    ) -> list[FinancialEvent]:
        if (occurred_at is None) != (uuid is None):
            raise ValueError("cursor timestamp and UUID must be provided together")
        direction = "ASC" if ascending else "DESC"
        where_clause, parameters = build_financial_event_filter(filters)
        if occurred_at is not None and uuid is not None:
            comparison = ">" if ascending else "<"
            where_clause += f" AND (event.occurred_at {comparison} ? OR (event.occurred_at = ? AND event.uuid {comparison} ?))"
            parameters.extend((occurred_at, occurred_at, uuid.bytes))
        rows = self.connection.execute(
            f"""
            SELECT event.uuid, event.occurred_at, event.description, event.type
            FROM financial_event AS event
            {where_clause}
            ORDER BY event.occurred_at {direction}, event.uuid {direction}
            LIMIT ?
            """,
            [*parameters, page_size],
        ).fetchall()
        return self._to_models(rows)

    def count_matching(self, filters: FinancialEventFilter) -> int:
        where_clause, parameters = build_financial_event_filter(filters)
        row = self.connection.execute(
            f"""
            SELECT COUNT(*)
            FROM financial_event AS event
            {where_clause}
            """,
            parameters,
        ).fetchone()
        return int(row[0])

    def _to_models(self, rows: list[sqlite3.Row]) -> list[FinancialEvent]:
        if not rows:
            return []
        events = {row["uuid"]: {**dict(row), "movements": []} for row in rows}
        placeholders = ", ".join("?" for _ in rows)
        movement_rows = self.connection.execute(
            f"""
            SELECT uuid, financial_event_uuid, account_uuid, category_uuid, value, quantity, item_name, special_type
            FROM financial_movement
            WHERE financial_event_uuid IN ({placeholders})
            ORDER BY financial_event_uuid ASC, uuid ASC
            """,
            [row["uuid"] for row in rows],
        ).fetchall()
        for movement_row in movement_rows:
            movement = FinancialMovement.model_validate(dict(movement_row))
            events[movement.financial_event_uuid.bytes]["movements"].append(movement)
        return [FinancialEvent.model_validate(events[row["uuid"]]) for row in rows]

    def count(self) -> int:
        return int(self.connection.execute("SELECT COUNT(*) FROM financial_event").fetchone()[0])

    def delete(self, uuid: UUID) -> None:
        self.connection.execute("DELETE FROM financial_event WHERE uuid = ?", (uuid.bytes,))
