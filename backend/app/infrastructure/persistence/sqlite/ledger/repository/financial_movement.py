import sqlite3
from uuid import UUID, uuid4

from app.domain.ledger.model.financial_movement import FinancialMovement, FinancialMovementItemName, FinancialMovementQuantity
from app.domain.ledger.repository.financial_movement import FinancialMovementRepository


class SqliteFinancialMovementRepository(FinancialMovementRepository):
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

    def delete(self, uuid: UUID) -> None:
        self.connection.execute("DELETE FROM financial_movement WHERE uuid = ?", (uuid.bytes,))

    @staticmethod
    def _to_model(row: sqlite3.Row) -> FinancialMovement:
        return FinancialMovement.model_validate(dict(row))
