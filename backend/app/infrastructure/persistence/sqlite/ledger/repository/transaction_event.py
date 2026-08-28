import sqlite3
from uuid import UUID, uuid4

from app.domain.ledger.model.tag import Tag
from app.domain.ledger.model.transaction_event import TransactionEvent, TransactionEventType
from app.domain.ledger.model.transaction_event_filter import TransactionEventFilter
from app.domain.ledger.repository.transaction_event import TransactionEventRepository


class SqliteTransactionEventRepository(TransactionEventRepository):
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, occurred_at: int, description: str, type: TransactionEventType) -> None:
        event = TransactionEvent(uuid=uuid4(), occurred_at=occurred_at, description=description, type=type)
        self.connection.execute(
            "INSERT INTO transaction_event(uuid, occurred_at, description, type) VALUES (?, ?, ?, ?)",
            (str(event.uuid), event.occurred_at, event.description, event.type),
        )

    def get(self, uuid: UUID) -> TransactionEvent | None:
        row = self.connection.execute(
            "SELECT uuid, occurred_at, description, type FROM transaction_event WHERE uuid = ?",
            (str(uuid),),
        ).fetchone()
        if row is None:
            return None
        return self._to_model(row)

    def update_occurred_at(self, uuid: UUID, value: int) -> None:
        event = TransactionEvent(uuid=uuid, occurred_at=value, description="event", type="TRANSACTION")
        self.connection.execute(
            "UPDATE transaction_event SET occurred_at = ? WHERE uuid = ?",
            (event.occurred_at, str(event.uuid)),
        )

    def update_description(self, uuid: UUID, value: str) -> None:
        event = TransactionEvent(uuid=uuid, occurred_at=0, description=value, type="TRANSACTION")
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
        return [self._to_model(row) for row in rows]

    def list_filtered(self, filters: TransactionEventFilter) -> list[TransactionEvent]:
        raise NotImplementedError("Filtered transaction-event queries are not implemented")

    def list_page(self, page_number: int, page_size: int, sort_key: str, ascending: bool, filters: TransactionEventFilter) -> list[TransactionEvent]:
        raise NotImplementedError("Filtered transaction-event pagination is not implemented")

    @staticmethod
    def _to_model(row: sqlite3.Row) -> TransactionEvent:
        return TransactionEvent.model_validate(dict(row))
