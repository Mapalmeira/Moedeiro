import sqlite3
from uuid import UUID, uuid4

from app.domain.ledger.model.financial_movement import FinancialMovement
from app.domain.ledger.repository.financial_movement import FinancialMovementRepository


class SqliteFinancialMovementRepository(FinancialMovementRepository):
    _SORT_COLUMNS = {
        "value": "value",
        "item_name": "item_name",
    }

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, transaction_event_uuid: UUID, account_uuid: UUID, category_uuid: UUID, value: int, item_name: str | None) -> FinancialMovement:
        movement = FinancialMovement(
            uuid=uuid4(),
            transaction_event_uuid=transaction_event_uuid,
            account_uuid=account_uuid,
            category_uuid=category_uuid,
            value=value,
            item_name=item_name,
        )
        self.connection.execute(
            """
            INSERT INTO financial_movement(uuid, transaction_event_uuid, account_uuid, category_uuid, value, item_name)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                movement.uuid.bytes,
                movement.transaction_event_uuid.bytes,
                movement.account_uuid.bytes,
                movement.category_uuid.bytes,
                movement.value,
                movement.item_name,
            ),
        )
        return movement

    def get(self, uuid: UUID) -> FinancialMovement | None:
        row = self.connection.execute(
            """
            SELECT uuid, transaction_event_uuid, account_uuid, category_uuid, value, item_name
            FROM financial_movement
            WHERE uuid = ?
            """,
            (uuid.bytes,),
        ).fetchone()
        if row is None:
            return None
        return self._to_model(row)

    def update_value(self, uuid: UUID, value: int) -> None:
        movement = self._validation_model(uuid, value=value)
        self.connection.execute(
            "UPDATE financial_movement SET value = ? WHERE uuid = ?",
            (movement.value, movement.uuid.bytes),
        )

    def update_item_name(self, uuid: UUID, value: str | None) -> None:
        movement = self._validation_model(uuid, item_name=value)
        self.connection.execute(
            "UPDATE financial_movement SET item_name = ? WHERE uuid = ?",
            (movement.item_name, movement.uuid.bytes),
        )

    def update_category(self, uuid: UUID, category_uuid: UUID) -> None:
        movement = self._validation_model(uuid, category_uuid=category_uuid)
        self.connection.execute(
            "UPDATE financial_movement SET category_uuid = ? WHERE uuid = ?",
            (movement.category_uuid.bytes, movement.uuid.bytes),
        )

    def list_by_transaction_event(self, transaction_event_uuid: UUID) -> list[FinancialMovement]:
        rows = self.connection.execute(
            """
            SELECT uuid, transaction_event_uuid, account_uuid, category_uuid, value, item_name
            FROM financial_movement
            WHERE transaction_event_uuid = ?
            """,
            (transaction_event_uuid.bytes,),
        ).fetchall()
        return [self._to_model(row) for row in rows]

    def list_all(self) -> list[FinancialMovement]:
        rows = self.connection.execute(
            "SELECT uuid, transaction_event_uuid, account_uuid, category_uuid, value, item_name FROM financial_movement"
        ).fetchall()
        return [self._to_model(row) for row in rows]

    def list_page(self, page_number: int, page_size: int, sort_key: str, ascending: bool) -> list[FinancialMovement]:
        self._validate_page(page_number, page_size)
        sort_column = self._get_sort_column(sort_key)
        direction = "ASC" if ascending else "DESC"
        offset = (page_number - 1) * page_size
        rows = self.connection.execute(
            f"""
            SELECT uuid, transaction_event_uuid, account_uuid, category_uuid, value, item_name
            FROM financial_movement
            ORDER BY {sort_column} {direction}, uuid ASC
            LIMIT ? OFFSET ?
            """,
            (page_size, offset),
        ).fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _validation_model(uuid: UUID, value: int = 1, item_name: str | None = None, category_uuid: UUID | None = None) -> FinancialMovement:
        return FinancialMovement(
            uuid=uuid,
            transaction_event_uuid=uuid,
            account_uuid=uuid,
            category_uuid=category_uuid or uuid,
            value=value,
            item_name=item_name,
        )

    @staticmethod
    def _to_model(row: sqlite3.Row) -> FinancialMovement:
        return FinancialMovement.model_validate(dict(row))

    @classmethod
    def _get_sort_column(cls, sort_key: str) -> str:
        try:
            return cls._SORT_COLUMNS[sort_key]
        except KeyError as error:
            raise ValueError(f"Invalid financial movement sort key: {sort_key}") from error

    @staticmethod
    def _validate_page(page_number: int, page_size: int) -> None:
        if page_number < 1:
            raise ValueError("page_number must be greater than or equal to 1")
        if page_size < 1:
            raise ValueError("page_size must be greater than or equal to 1")
