import sqlite3
from uuid import UUID, uuid4

from app.domain.ledger.model.financial_movement import FinancialMovement
from app.domain.ledger.model.tag import Tag
from app.domain.ledger.model.transaction_event import TransactionEvent, TransactionEventType
from app.domain.ledger.model.transaction_event_filter import TransactionEventFilter
from app.domain.ledger.repository.transaction_event import TransactionEventRepository
from app.infrastructure.persistence.sqlite.ledger.repository._transaction_event_filter import build_transaction_event_filter


class SqliteTransactionEventRepository(TransactionEventRepository):
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, occurred_at: int, description: str, type: TransactionEventType) -> TransactionEvent:
        event = TransactionEvent(uuid=uuid4(), occurred_at=occurred_at, description=description, type=type, movements=[])
        self.connection.execute(
            "INSERT INTO transaction_event(uuid, occurred_at, description, type) VALUES (?, ?, ?, ?)",
            (str(event.uuid), event.occurred_at, event.description, event.type),
        )
        return event

    def get(self, uuid: UUID) -> TransactionEvent | None:
        row = self.connection.execute(
            "SELECT uuid, occurred_at, description, type FROM transaction_event WHERE uuid = ?",
            (str(uuid),),
        ).fetchone()
        if row is None:
            return None
        return self._to_models([row])[0]

    def update_occurred_at(self, uuid: UUID, value: int) -> None:
        event = TransactionEvent(uuid=uuid, occurred_at=value, description="event", type="TRANSACTION", movements=[])
        self.connection.execute(
            "UPDATE transaction_event SET occurred_at = ? WHERE uuid = ?",
            (event.occurred_at, str(event.uuid)),
        )

    def update_description(self, uuid: UUID, value: str) -> None:
        event = TransactionEvent(uuid=uuid, occurred_at=0, description=value, type="TRANSACTION", movements=[])
        self.connection.execute(
            "UPDATE transaction_event SET description = ? WHERE uuid = ?",
            (event.description, str(event.uuid)),
        )

    def add_tag(self, transaction_event_uuid: UUID, tag_uuid: UUID) -> None:
        self.connection.execute(
            "INSERT INTO transaction_tag(transaction_event_uuid, tag_uuid) VALUES (?, ?)",
            (str(transaction_event_uuid), str(tag_uuid)),
        )

    def remove_tag(self, transaction_event_uuid: UUID, tag_uuid: UUID) -> None:
        self.connection.execute(
            "DELETE FROM transaction_tag WHERE transaction_event_uuid = ? AND tag_uuid = ?",
            (str(transaction_event_uuid), str(tag_uuid)),
        )

    def list_tags(self, transaction_event_uuid: UUID) -> list[Tag]:
        rows = self.connection.execute(
            """
            SELECT tag.uuid, tag.name
            FROM tag
            JOIN transaction_tag ON transaction_tag.tag_uuid = tag.uuid
            WHERE transaction_tag.transaction_event_uuid = ?
            """,
            (str(transaction_event_uuid),),
        ).fetchall()
        return [Tag.model_validate(dict(row)) for row in rows]

    def list_all(self) -> list[TransactionEvent]:
        rows = self.connection.execute(
            "SELECT uuid, occurred_at, description, type FROM transaction_event"
        ).fetchall()
        return self._to_models(rows)

    def list_filtered(self, filters: TransactionEventFilter) -> list[TransactionEvent]:
        where_clause, parameters = build_transaction_event_filter(filters)
        rows = self.connection.execute(
            f"""
            SELECT event.uuid, event.occurred_at, event.description, event.type
            FROM transaction_event AS event
            {where_clause}
            """,
            parameters,
        ).fetchall()
        return self._to_models(rows)

    def list_page(self, page_number: int, page_size: int, ascending: bool, filters: TransactionEventFilter) -> list[TransactionEvent]:
        self._validate_page(page_number, page_size)
        direction = "ASC" if ascending else "DESC"
        offset = (page_number - 1) * page_size
        where_clause, parameters = build_transaction_event_filter(filters)
        rows = self.connection.execute(
            f"""
            SELECT event.uuid, event.occurred_at, event.description, event.type
            FROM transaction_event AS event
            {where_clause}
            ORDER BY event.occurred_at {direction}, event.uuid ASC
            LIMIT ? OFFSET ?
            """,
            [*parameters, page_size, offset],
        ).fetchall()
        return self._to_models(rows)

    def _to_models(self, rows: list[sqlite3.Row]) -> list[TransactionEvent]:
        if not rows:
            return []
        events = {row["uuid"]: {**dict(row), "movements": []} for row in rows}
        placeholders = ", ".join("?" for _ in rows)
        movement_rows = self.connection.execute(
            f"""
            SELECT uuid, transaction_event_uuid, account_uuid, category_uuid, value, item_name
            FROM financial_movement
            WHERE transaction_event_uuid IN ({placeholders})
            """,
            [row["uuid"] for row in rows],
        ).fetchall()
        for movement_row in movement_rows:
            movement = FinancialMovement.model_validate(dict(movement_row))
            events[str(movement.transaction_event_uuid)]["movements"].append(movement)
        return [TransactionEvent.model_validate(events[row["uuid"]]) for row in rows]

    @staticmethod
    def _validate_page(page_number: int, page_size: int) -> None:
        if page_number < 1:
            raise ValueError("page_number must be greater than or equal to 1")
        if page_size < 1:
            raise ValueError("page_size must be greater than or equal to 1")
