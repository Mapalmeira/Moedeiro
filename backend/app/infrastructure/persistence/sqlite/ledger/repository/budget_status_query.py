import sqlite3
from uuid import UUID

from app.domain.ledger.model.budget_status import BudgetStatus
from app.domain.ledger.repository.budget_status_query import BudgetStatusQueryRepository


class SqliteBudgetStatusQueryRepository(BudgetStatusQueryRepository):
    _SELECT = """
        WITH RECURSIVE active_budgets AS MATERIALIZED (
            SELECT
                budget.uuid,
                budget.amount,
                budget.category_uuid,
                budget.currency_uuid,
                budget.from_timestamp
            FROM budget
            {budget_where}
        ),
        selected_budgets AS (
            SELECT
                budget.uuid,
                budget.amount,
                budget.category_uuid,
                budget.currency_uuid,
                budget.from_timestamp,
                COUNT(budget_accounts.account_uuid) AS account_count
            FROM active_budgets AS budget
            LEFT JOIN budget_accounts ON budget_accounts.budget_uuid = budget.uuid
            GROUP BY budget.uuid
        ),
        category_descendants(root_uuid, uuid) AS (
            SELECT category_uuid, category_uuid
            FROM selected_budgets

            UNION

            SELECT parent.root_uuid, child.uuid
            FROM category_descendants AS parent
            JOIN category AS child ON child.parent_uuid = parent.uuid
        )
        SELECT
            budget.uuid AS budget_uuid,
            budget.amount AS budgeted_amount,
            COALESCE(SUM(
                CASE
                    WHEN event.uuid IS NOT NULL
                     AND account.uuid IS NOT NULL
                     AND (budget.account_count = 0 OR selected_account.account_uuid IS NOT NULL)
                    THEN -movement.value
                    ELSE 0
                END
            ), 0) AS spent_amount
        FROM selected_budgets AS budget
        LEFT JOIN category_descendants AS descendant ON descendant.root_uuid = budget.category_uuid
        LEFT JOIN financial_movement AS movement ON movement.category_uuid = descendant.uuid AND movement.value < 0
        LEFT JOIN financial_event AS event
          ON event.uuid = movement.financial_event_uuid
         AND event.type <> 'ACCOUNT_TRANSFER'
         AND event.occurred_at >= budget.from_timestamp
         AND event.occurred_at <= ?
        LEFT JOIN account
          ON account.uuid = movement.account_uuid
         AND account.currency_uuid = budget.currency_uuid
        LEFT JOIN budget_accounts AS selected_account
          ON selected_account.budget_uuid = budget.uuid
         AND selected_account.account_uuid = movement.account_uuid
        GROUP BY budget.uuid, budget.amount
    """

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def get_status(self, budget_uuid: UUID, timestamp: int) -> BudgetStatus | None:
        row = self.connection.execute(
            self._SELECT.format(budget_where="WHERE budget.uuid = ? AND budget.from_timestamp <= ? AND budget.to_timestamp > ?"),
            (budget_uuid.bytes, timestamp, timestamp, timestamp),
        ).fetchone()
        if row is None:
            return None
        return self._to_model(row)

    def list_statuses(self, timestamp: int) -> list[BudgetStatus]:
        rows = self.connection.execute(
            self._SELECT.format(budget_where="WHERE budget.from_timestamp <= ? AND budget.to_timestamp > ?"),
            (timestamp, timestamp, timestamp),
        ).fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: sqlite3.Row) -> BudgetStatus:
        values = dict(row)
        values["over_budget"] = values["spent_amount"] > values["budgeted_amount"]
        return BudgetStatus.model_validate(values)
