import sqlite3
from uuid import UUID

from app.domain.ledger.model.cash_flow import CashFlow
from app.domain.ledger.model.financial_event_filter import FinancialEventFilter
from app.domain.ledger.repository.cash_flow_query import CashFlowQueryRepository
from app.infrastructure.persistence.sqlite.ledger.repository._financial_event_filter import build_financial_event_filter


class SqliteCashFlowQueryRepository(CashFlowQueryRepository):
    _SECONDS_PER_DAY = 86400

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def get_summary(self, currency_uuid: UUID, filters: FinancialEventFilter) -> CashFlow:
        where_clause, parameters = self._filtered_events(filters)
        movement_clause, movement_parameters = self._movement_filter(filters)
        row = self.connection.execute(
            f"""
            WITH filtered_events AS (
                SELECT event.uuid, event.occurred_at
                FROM financial_event AS event
                {where_clause}
            )
            SELECT
                COALESCE(SUM(CASE WHEN movement.value > 0 THEN movement.value ELSE 0 END), 0) AS income,
                COALESCE(SUM(CASE WHEN movement.value < 0 THEN -movement.value ELSE 0 END), 0) AS expense,
                COUNT(DISTINCT filtered_events.uuid) AS event_count,
                COALESCE(SUM(CASE WHEN movement.value > 0 THEN 1 ELSE 0 END), 0) AS income_movement_count,
                COALESCE(SUM(CASE WHEN movement.value < 0 THEN 1 ELSE 0 END), 0) AS expense_movement_count
            FROM filtered_events
            JOIN financial_movement AS movement ON movement.financial_event_uuid = filtered_events.uuid
            JOIN account ON account.uuid = movement.account_uuid
            WHERE account.currency_uuid = ?{movement_clause}
            """,
            [*parameters, currency_uuid.bytes, *movement_parameters],
        ).fetchone()
        return self._to_model(row, currency_uuid)

    def list_points(self, currency_uuid: UUID, filters: FinancialEventFilter) -> list[CashFlow]:
        from_timestamp, to_timestamp = self._validate_point_period(filters)
        where_clause, parameters = self._filtered_events(filters)
        movement_clause, movement_parameters = self._movement_filter(filters)
        rows = self.connection.execute(
            f"""
            WITH filtered_events AS (
                SELECT event.uuid, event.occurred_at,
                       ? + ((event.occurred_at - ?) / {self._SECONDS_PER_DAY}) * {self._SECONDS_PER_DAY} AS day_start
                FROM financial_event AS event
                {where_clause}
            )
            SELECT
                filtered_events.day_start,
                COALESCE(SUM(CASE WHEN movement.value > 0 THEN movement.value ELSE 0 END), 0) AS income,
                COALESCE(SUM(CASE WHEN movement.value < 0 THEN -movement.value ELSE 0 END), 0) AS expense,
                COUNT(DISTINCT filtered_events.uuid) AS event_count,
                COALESCE(SUM(CASE WHEN movement.value > 0 THEN 1 ELSE 0 END), 0) AS income_movement_count,
                COALESCE(SUM(CASE WHEN movement.value < 0 THEN 1 ELSE 0 END), 0) AS expense_movement_count
            FROM filtered_events
            JOIN financial_movement AS movement ON movement.financial_event_uuid = filtered_events.uuid
            JOIN account ON account.uuid = movement.account_uuid
            WHERE account.currency_uuid = ?{movement_clause}
            GROUP BY filtered_events.day_start
            """,
            [from_timestamp, from_timestamp, *parameters, currency_uuid.bytes, *movement_parameters],
        ).fetchall()
        rows_by_day = {row["day_start"]: row for row in rows}
        return [
            self._to_model(rows_by_day.get(day_start), currency_uuid)
            for day_start in range(from_timestamp, to_timestamp, self._SECONDS_PER_DAY)
        ]

    @classmethod
    def _validate_point_period(cls, filters: FinancialEventFilter) -> tuple[int, int]:
        if (filters.to_timestamp - filters.from_timestamp) % cls._SECONDS_PER_DAY != 0:
            raise ValueError("the interval must contain complete 24-hour days")
        return filters.from_timestamp, filters.to_timestamp

    @staticmethod
    def _filtered_events(filters: FinancialEventFilter) -> tuple[str, list[bytes | str | int]]:
        where_clause, parameters = build_financial_event_filter(filters)
        return where_clause + " AND event.type <> ?", [*parameters, "ACCOUNT_TRANSFER"]

    @staticmethod
    def _movement_filter(filters: FinancialEventFilter) -> tuple[str, list[bytes]]:
        clauses: list[str] = []
        parameters: list[bytes] = []
        if filters.account_uuid is not None:
            clauses.append("movement.account_uuid = ?")
            parameters.append(filters.account_uuid.bytes)
        if filters.category_uuids:
            placeholders = ", ".join("?" for _ in filters.category_uuids)
            clauses.append(
                f"""
                movement.category_uuid IN (
                    WITH RECURSIVE category_descendants(uuid) AS (
                        SELECT uuid
                        FROM category
                        WHERE uuid IN ({placeholders})

                        UNION

                        SELECT child.uuid
                        FROM category AS child
                        JOIN category_descendants AS parent ON child.parent_uuid = parent.uuid
                    )
                    SELECT uuid FROM category_descendants
                )
                """
            )
            parameters.extend(sorted(uuid.bytes for uuid in filters.category_uuids))
        if not clauses:
            return "", parameters
        return " AND " + " AND ".join(clauses), parameters

    @staticmethod
    def _to_model(row: sqlite3.Row | None, currency_uuid: UUID) -> CashFlow:
        return CashFlow(
            currency_uuid=currency_uuid,
            income=0 if row is None else row["income"],
            expense=0 if row is None else row["expense"],
            event_count=0 if row is None else row["event_count"],
            income_movement_count=0 if row is None else row["income_movement_count"],
            expense_movement_count=0 if row is None else row["expense_movement_count"],
        )
