import sqlite3
from uuid import UUID

from app.domain.ledger.model.budget_status import BudgetStatus
from app.domain.ledger.repository.budget_status_query import BudgetStatusQueryRepository


class SqliteBudgetStatusQueryRepository(BudgetStatusQueryRepository):
    _SELECT = """
        WITH RECURSIVE category_descendants(root_uuid, uuid) AS (
            SELECT uuid, uuid
            FROM category

            UNION

            SELECT parent.root_uuid, child.uuid
            FROM category_descendants AS parent
            JOIN category AS child ON child.parent_uuid = parent.uuid
        )
        SELECT
            budget.uuid AS budget_uuid,
            budget.amount AS budgeted_amount,
            COALESCE((
                SELECT SUM(-movement.value)
                FROM budget_accounts
                JOIN financial_movement AS movement ON movement.account_uuid = budget_accounts.account_uuid
                JOIN transaction_event AS event ON event.uuid = movement.transaction_event_uuid
                WHERE budget_accounts.budget_uuid = budget.uuid
                  AND movement.category_uuid IN (
                      SELECT uuid
                      FROM category_descendants
                      WHERE root_uuid = budget.category_uuid
                  )
                  AND movement.value < 0
                  AND event.type <> 'ACCOUNT_TRANSFER'
                  AND event.occurred_at >= budget.from_timestamp
                  AND event.occurred_at <= ?
            ), 0) AS spent_amount
        FROM budget
    """

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def get_status(self, budget_uuid: UUID, timestamp: int) -> BudgetStatus | None:
        row = self.connection.execute(
            self._SELECT + " WHERE budget.uuid = ? AND budget.from_timestamp <= ? AND budget.to_timestamp > ?",
            (timestamp, budget_uuid.bytes, timestamp, timestamp),
        ).fetchone()
        if row is None:
            return None
        return self._to_model(row)

    def list_statuses(self, timestamp: int) -> list[BudgetStatus]:
        rows = self.connection.execute(
            self._SELECT + " WHERE budget.from_timestamp <= ? AND budget.to_timestamp > ?",
            (timestamp, timestamp, timestamp),
        ).fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: sqlite3.Row) -> BudgetStatus:
        values = dict(row)
        values["over_budget"] = values["spent_amount"] > values["budgeted_amount"]
        return BudgetStatus.model_validate(values)
