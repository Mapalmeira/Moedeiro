import sqlite3
from uuid import UUID, uuid4

from app.domain.ledger.model.financial_movement import FinancialMovement, FinancialMovementItemName, FinancialMovementQuantity
from app.domain.ledger.repository.financial_movement import FinancialMovementRepository


class SqliteFinancialMovementRepository(FinancialMovementRepository):
    _SORT_COLUMNS = {
        "value": "value",
        "quantity": "quantity",
        "item_name": "item_name",
    }

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, financial_event_uuid: UUID, account_uuid: UUID, category_uuid: UUID, value: int, item_name: FinancialMovementItemName | None, quantity: FinancialMovementQuantity = 1) -> FinancialMovement:
        movement = FinancialMovement(
            uuid=uuid4(),
            financial_event_uuid=financial_event_uuid,
            account_uuid=account_uuid,
            category_uuid=category_uuid,
            value=value,
            quantity=quantity,
            item_name=item_name,
        )
        self.connection.execute(
            """
            INSERT INTO financial_movement(uuid, financial_event_uuid, account_uuid, category_uuid, value, quantity, item_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                movement.uuid.bytes,
                movement.financial_event_uuid.bytes,
                movement.account_uuid.bytes,
                movement.category_uuid.bytes,
                movement.value,
                movement.quantity,
                movement.item_name,
            ),
        )
        return movement

    def get(self, uuid: UUID) -> FinancialMovement | None:
        row = self.connection.execute(
            """
            SELECT uuid, financial_event_uuid, account_uuid, category_uuid, value, quantity, item_name
            FROM financial_movement
            WHERE uuid = ?
            """,
            (uuid.bytes,),
        ).fetchone()
        if row is None:
            return None
        return self._to_model(row)

    def update(self, movement: FinancialMovement) -> None:
        self.connection.execute(
            """
            UPDATE financial_movement
            SET account_uuid = ?, category_uuid = ?, value = ?, quantity = ?, item_name = ?
            WHERE uuid = ?
            """,
            (
                movement.account_uuid.bytes,
                movement.category_uuid.bytes,
                movement.value,
                movement.quantity,
                movement.item_name,
                movement.uuid.bytes,
            ),
        )

    def update_value(self, uuid: UUID, value: int) -> None:
        movement = self._validation_model(uuid, value=value)
        self.connection.execute(
            "UPDATE financial_movement SET value = ? WHERE uuid = ?",
            (movement.value, movement.uuid.bytes),
        )

    def update_quantity(self, uuid: UUID, quantity: FinancialMovementQuantity) -> None:
        movement = self._validation_model(uuid, quantity=quantity)
        self.connection.execute(
            "UPDATE financial_movement SET quantity = ? WHERE uuid = ?",
            (movement.quantity, movement.uuid.bytes),
        )

    def update_item_name(self, uuid: UUID, value: FinancialMovementItemName | None) -> None:
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

    def update_account(self, uuid: UUID, account_uuid: UUID) -> None:
        movement = self._validation_model(uuid, account_uuid=account_uuid)
        self.connection.execute(
            "UPDATE financial_movement SET account_uuid = ? WHERE uuid = ?",
            (movement.account_uuid.bytes, movement.uuid.bytes),
        )

    def list_by_financial_event(self, financial_event_uuid: UUID) -> list[FinancialMovement]:
        rows = self.connection.execute(
            """
            SELECT uuid, financial_event_uuid, account_uuid, category_uuid, value, quantity, item_name
            FROM financial_movement
            WHERE financial_event_uuid = ?
            """,
            (financial_event_uuid.bytes,),
        ).fetchall()
        return [self._to_model(row) for row in rows]

    def list_all(self, sort_key: str, ascending: bool) -> list[FinancialMovement]:
        sort_column = self._sort_column(sort_key)
        direction = "ASC" if ascending else "DESC"
        rows = self.connection.execute(
            f"SELECT uuid, financial_event_uuid, account_uuid, category_uuid, value, quantity, item_name FROM financial_movement ORDER BY {sort_column} {direction}, uuid ASC"
        ).fetchall()
        return [self._to_model(row) for row in rows]

    def delete(self, uuid: UUID) -> None:
        self.connection.execute("DELETE FROM financial_movement WHERE uuid = ?", (uuid.bytes,))

    @classmethod
    def _sort_column(cls, sort_key: str) -> str:
        try:
            return cls._SORT_COLUMNS[sort_key]
        except KeyError as error:
            raise ValueError(f"Unsupported financial movement sort key: {sort_key}") from error

    @staticmethod
    def _validation_model(uuid: UUID, value: int = 1, quantity: FinancialMovementQuantity = 1, item_name: FinancialMovementItemName | None = None, category_uuid: UUID | None = None, account_uuid: UUID | None = None) -> FinancialMovement:
        return FinancialMovement(
            uuid=uuid,
            financial_event_uuid=uuid,
            account_uuid=account_uuid or uuid,
            category_uuid=category_uuid or uuid,
            value=value,
            quantity=quantity,
            item_name=item_name,
        )

    @staticmethod
    def _to_model(row: sqlite3.Row) -> FinancialMovement:
        return FinancialMovement.model_validate(dict(row))
