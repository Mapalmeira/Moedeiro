import sqlite3
from uuid import UUID, uuid4

from app.domain.ledger.model.budget import Budget, BudgetAmount, BudgetDescription, BudgetName
from app.domain.ledger.repository.budget import BudgetRepository


class SqliteBudgetRepository(BudgetRepository):
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(
        self,
        account_uuid: UUID,
        category_uuid: UUID,
        from_timestamp: int,
        to_timestamp: int,
        name: BudgetName,
        description: BudgetDescription,
        amount: BudgetAmount,
    ) -> Budget:
        budget = Budget(
            uuid=uuid4(),
            account_uuid=account_uuid,
            category_uuid=category_uuid,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            name=name,
            description=description,
            amount=amount,
        )
        self.connection.execute(
            """
            INSERT INTO budget(uuid, account_uuid, category_uuid, from_timestamp, to_timestamp, budget_name, description, amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                budget.uuid.bytes,
                budget.account_uuid.bytes,
                budget.category_uuid.bytes,
                budget.from_timestamp,
                budget.to_timestamp,
                budget.name,
                budget.description,
                budget.amount,
            ),
        )
        return budget

    def get(self, uuid: UUID) -> Budget | None:
        row = self.connection.execute(
            """
            SELECT uuid, account_uuid, category_uuid, from_timestamp, to_timestamp, budget_name AS name, description, amount
            FROM budget
            WHERE uuid = ?
            """,
            (uuid.bytes,),
        ).fetchone()
        return None if row is None else self._to_model(row)

    def get_by_name(self, name: BudgetName) -> Budget | None:
        row = self.connection.execute(
            """
            SELECT uuid, account_uuid, category_uuid, from_timestamp, to_timestamp, budget_name AS name, description, amount
            FROM budget
            WHERE budget_name = ?
            """,
            (name,),
        ).fetchone()
        return None if row is None else self._to_model(row)

    def update(self, budget: Budget) -> None:
        self.connection.execute(
            """
            UPDATE budget
            SET category_uuid = ?, from_timestamp = ?, to_timestamp = ?, budget_name = ?, description = ?, amount = ?
            WHERE uuid = ?
            """,
            (
                budget.category_uuid.bytes,
                budget.from_timestamp,
                budget.to_timestamp,
                budget.name,
                budget.description,
                budget.amount,
                budget.uuid.bytes,
            ),
        )

    def count(self) -> int:
        return int(self.connection.execute("SELECT COUNT(*) FROM budget").fetchone()[0])

    def delete(self, uuid: UUID) -> None:
        self.connection.execute("DELETE FROM budget WHERE uuid = ?", (uuid.bytes,))

    @staticmethod
    def _to_model(row: sqlite3.Row) -> Budget:
        return Budget.model_validate(dict(row))
