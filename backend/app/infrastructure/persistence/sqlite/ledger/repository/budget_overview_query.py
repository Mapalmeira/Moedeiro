import sqlite3
from collections.abc import Collection
from uuid import UUID

from app.domain.ledger.model.budget import Budget
from app.domain.ledger.model.budget_overview import BudgetOverviewItem, BudgetOverviewState
from app.domain.ledger.repository.budget_overview_query import BudgetOverviewQueryRepository
from app.infrastructure.persistence.sqlite.ledger.repository._numeric import raise_query_result_overflow, require_sqlite_integer


class SqliteBudgetOverviewQueryRepository(BudgetOverviewQueryRepository):
    _BUDGET_COLUMNS = """
        budget.uuid,
        budget.account_uuid,
        budget.category_uuid,
        budget.from_timestamp,
        budget.to_timestamp,
        budget.budget_name,
        budget.description,
        budget.amount,
        budget.icon,
        budget.color_code
    """

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def list_page(
        self,
        timestamp: int,
        states: Collection[BudgetOverviewState],
        account_uuid: UUID | None,
        search: str | None,
        page_size: int,
        cursor_name: str | None,
        cursor_uuid: UUID | None,
    ) -> list[BudgetOverviewItem]:
        selected_states = tuple(dict.fromkeys(states))
        if not selected_states:
            return []
        if (cursor_name is None) != (cursor_uuid is None):
            raise ValueError("budget overview cursor name and UUID must be provided together")

        conditions = [f"state IN ({', '.join('?' for _ in selected_states)})"]
        parameters: list[object] = [timestamp, timestamp, *selected_states]
        if account_uuid is not None:
            conditions.append("account_uuid = ?")
            parameters.append(account_uuid.bytes)
        if search:
            conditions.append("LOWER(budget_name) LIKE ? ESCAPE '\\'")
            parameters.append(f"%{self._escape_like(search.lower())}%")
        if cursor_name is not None and cursor_uuid is not None:
            conditions.append("(budget_name > ? OR (budget_name = ? AND uuid > ?))")
            parameters.extend((cursor_name, cursor_name, cursor_uuid.bytes))
        parameters.extend((page_size, timestamp + 1))

        query = f"""
            WITH RECURSIVE classified_budgets AS (
                SELECT
                    {self._BUDGET_COLUMNS},
                    CASE
                        WHEN budget.from_timestamp > ? THEN 'FUTURE'
                        WHEN budget.to_timestamp <= ? THEN 'FINISHED'
                        ELSE 'ACTIVE'
                    END AS state
                FROM budget
            ),
            selected_budgets AS MATERIALIZED (
                SELECT *
                FROM classified_budgets
                WHERE {' AND '.join(conditions)}
                ORDER BY budget_name ASC, uuid ASC
                LIMIT ?
            ),
            category_descendants(root_uuid, uuid) AS (
                SELECT uuid, category_uuid
                FROM selected_budgets
                WHERE state <> 'FUTURE'

                UNION

                SELECT parent.root_uuid, child.uuid
                FROM category_descendants AS parent
                JOIN category AS child ON child.parent_uuid = parent.uuid
            ),
            spending AS (
                SELECT
                    budget.uuid AS budget_uuid,
                    COALESCE(SUM(
                        CASE WHEN event.uuid IS NOT NULL THEN -movement.value * movement.quantity ELSE 0 END
                    ), 0) AS spent_amount
                FROM selected_budgets AS budget
                LEFT JOIN category_descendants AS descendant ON descendant.root_uuid = budget.uuid
                LEFT JOIN financial_movement AS movement
                  ON movement.category_uuid = descendant.uuid
                 AND movement.account_uuid = budget.account_uuid
                 AND movement.value < 0
                LEFT JOIN financial_event AS event
                  ON event.uuid = movement.financial_event_uuid
                 AND event.type <> 'ACCOUNT_TRANSFER'
                 AND event.occurred_at >= budget.from_timestamp
                 AND event.occurred_at < CASE WHEN budget.state = 'ACTIVE' THEN ? ELSE budget.to_timestamp END
                WHERE budget.state <> 'FUTURE'
                GROUP BY budget.uuid
            )
            SELECT
                selected_budgets.*,
                CASE WHEN selected_budgets.state = 'FUTURE' THEN NULL ELSE COALESCE(spending.spent_amount, 0) END AS spent_amount
            FROM selected_budgets
            LEFT JOIN spending ON spending.budget_uuid = selected_budgets.uuid
            ORDER BY selected_budgets.budget_name ASC, selected_budgets.uuid ASC
        """
        try:
            rows = self.connection.execute(query, parameters).fetchall()
        except sqlite3.OperationalError as error:
            raise_query_result_overflow(error)
        return [self._to_overview(row) for row in rows]

    def list_attention(self, timestamp: int, account_uuid: UUID, limit: int) -> list[BudgetOverviewItem]:
        query = f"""
            WITH RECURSIVE active_budgets AS MATERIALIZED (
                SELECT {self._BUDGET_COLUMNS}, 'ACTIVE' AS state
                FROM budget
                WHERE budget.account_uuid = ?
                  AND budget.from_timestamp <= ?
                  AND budget.to_timestamp > ?
            ),
            category_descendants(root_uuid, uuid) AS (
                SELECT uuid, category_uuid FROM active_budgets

                UNION

                SELECT parent.root_uuid, child.uuid
                FROM category_descendants AS parent
                JOIN category AS child ON child.parent_uuid = parent.uuid
            ),
            spending AS (
                SELECT
                    budget.uuid AS budget_uuid,
                    COALESCE(SUM(
                        CASE WHEN event.uuid IS NOT NULL THEN -movement.value * movement.quantity ELSE 0 END
                    ), 0) AS spent_amount
                FROM active_budgets AS budget
                LEFT JOIN category_descendants AS descendant ON descendant.root_uuid = budget.uuid
                LEFT JOIN financial_movement AS movement
                  ON movement.category_uuid = descendant.uuid
                 AND movement.account_uuid = budget.account_uuid
                 AND movement.value < 0
                LEFT JOIN financial_event AS event
                  ON event.uuid = movement.financial_event_uuid
                 AND event.type <> 'ACCOUNT_TRANSFER'
                 AND event.occurred_at >= budget.from_timestamp
                 AND event.occurred_at < ?
                GROUP BY budget.uuid
            )
            SELECT active_budgets.*, COALESCE(spending.spent_amount, 0) AS spent_amount
            FROM active_budgets
            LEFT JOIN spending ON spending.budget_uuid = active_budgets.uuid
            ORDER BY
                (COALESCE(spending.spent_amount, 0) > active_budgets.amount) DESC,
                CASE
                    WHEN active_budgets.amount = 0 AND COALESCE(spending.spent_amount, 0) > 0 THEN 1.0e308
                    WHEN active_budgets.amount = 0 THEN 0.0
                    ELSE CAST(COALESCE(spending.spent_amount, 0) AS REAL) / active_budgets.amount
                END DESC,
                active_budgets.to_timestamp ASC,
                active_budgets.budget_name ASC,
                active_budgets.uuid ASC
            LIMIT ?
        """
        try:
            rows = self.connection.execute(query, (account_uuid.bytes, timestamp, timestamp, timestamp + 1, limit)).fetchall()
        except sqlite3.OperationalError as error:
            raise_query_result_overflow(error)
        return [self._to_overview(row) for row in rows]

    @staticmethod
    def _escape_like(value: str) -> str:
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    @staticmethod
    def _to_overview(row: sqlite3.Row) -> BudgetOverviewItem:
        values = dict(row)
        budget = Budget.model_validate(
            {
                "uuid": values["uuid"],
                "account_uuid": values["account_uuid"],
                "category_uuid": values["category_uuid"],
                "from_timestamp": values["from_timestamp"],
                "to_timestamp": values["to_timestamp"],
                "name": values["budget_name"],
                "description": values["description"],
                "amount": values["amount"],
                "icon": values["icon"],
                "color_code": values["color_code"],
            }
        )
        state: BudgetOverviewState = values["state"]
        spent_amount = None if values["spent_amount"] is None else require_sqlite_integer(values["spent_amount"])
        fulfilled = state == "FINISHED" and spent_amount is not None and spent_amount <= budget.amount
        return BudgetOverviewItem(
            budget=budget,
            state=state,
            spent_amount=spent_amount,
            fulfilled=fulfilled if state == "FINISHED" else None,
        )
