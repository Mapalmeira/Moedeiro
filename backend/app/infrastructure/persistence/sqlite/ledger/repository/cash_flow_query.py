import sqlite3
from uuid import UUID

from app.domain.ledger.model.cash_flow import CashFlow
from app.domain.ledger.model.transaction_event_filter import TransactionEventFilter
from app.domain.ledger.repository.cash_flow_query import CashFlowQueryRepository
from app.infrastructure.persistence.sqlite.ledger.repository._transaction_event_filter import build_transaction_event_filter


class SqliteCashFlowQueryRepository(CashFlowQueryRepository):
    _SECONDS_PER_DAY = 86400

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def get_summary(self, currency_uuid: UUID, filters: TransactionEventFilter) -> CashFlow | None:
        where_clause, parameters = self._filtered_events(filters)
        row = self.connection.execute(
            f"""
            WITH filtered_events AS (
                SELECT event.uuid, event.occurred_at
                FROM transaction_event AS event
                {where_clause}
            )
            SELECT
                MIN(filtered_events.occurred_at) AS first_timestamp,
                MAX(filtered_events.occurred_at) AS last_timestamp,
                COALESCE(SUM(CASE WHEN movement.value > 0 THEN movement.value ELSE 0 END), 0) AS income,
                COALESCE(SUM(CASE WHEN movement.value < 0 THEN -movement.value ELSE 0 END), 0) AS expense,
                COUNT(DISTINCT filtered_events.uuid) AS event_count,
                COALESCE(SUM(CASE WHEN movement.value > 0 THEN 1 ELSE 0 END), 0) AS income_movement_count,
                COALESCE(SUM(CASE WHEN movement.value < 0 THEN 1 ELSE 0 END), 0) AS expense_movement_count
            FROM filtered_events
            JOIN financial_movement AS movement ON movement.transaction_event_uuid = filtered_events.uuid
            JOIN account ON account.uuid = movement.account_uuid
            WHERE account.currency_uuid = ?
            """,
            [*parameters, str(currency_uuid)],
        ).fetchone()
        from_timestamp = filters.from_timestamp if filters.from_timestamp is not None else row["first_timestamp"]
        to_timestamp = filters.to_timestamp if filters.to_timestamp is not None else row["last_timestamp"]
        if from_timestamp is None or to_timestamp is None:
            return None
        return self._to_model(row, currency_uuid, from_timestamp, to_timestamp)

    def list_points(self, currency_uuid: UUID, filters: TransactionEventFilter) -> list[CashFlow]:
        from_timestamp, to_timestamp = self._validate_point_period(filters)
        where_clause, parameters = self._filtered_events(filters)
        rows = self.connection.execute(
            f"""
            WITH filtered_events AS (
                SELECT event.uuid, event.occurred_at,
                       ? + ((event.occurred_at - ?) / {self._SECONDS_PER_DAY}) * {self._SECONDS_PER_DAY} AS day_start
                FROM transaction_event AS event
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
            JOIN financial_movement AS movement ON movement.transaction_event_uuid = filtered_events.uuid
            JOIN account ON account.uuid = movement.account_uuid
            WHERE account.currency_uuid = ?
            GROUP BY filtered_events.day_start
            """,
            [from_timestamp, from_timestamp, *parameters, str(currency_uuid)],
        ).fetchall()
        points = [
            self._to_model(row, currency_uuid, row["day_start"], row["day_start"] + self._SECONDS_PER_DAY)
            for row in rows
        ]
        return sorted(points, key=lambda point: point.from_timestamp)

    @classmethod
    def _validate_point_period(cls, filters: TransactionEventFilter) -> tuple[int, int]:
        if filters.from_timestamp is None or filters.to_timestamp is None:
            raise ValueError("cash-flow points require from_timestamp and to_timestamp")
        if (filters.to_timestamp - filters.from_timestamp) % cls._SECONDS_PER_DAY != 0:
            raise ValueError("the interval must contain complete 24-hour days")
        return filters.from_timestamp, filters.to_timestamp

    @staticmethod
    def _filtered_events(filters: TransactionEventFilter) -> tuple[str, list[str | int]]:
        where_clause, parameters = build_transaction_event_filter(filters)
        conjunction = " AND " if where_clause else "WHERE "
        return where_clause + conjunction + "event.type <> ?", [*parameters, "ACCOUNT_TRANSFER"]

    @staticmethod
    def _to_model(row: sqlite3.Row, currency_uuid: UUID, from_timestamp: int, to_timestamp: int) -> CashFlow:
        return CashFlow(
            currency_uuid=currency_uuid,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            income=row["income"],
            expense=row["expense"],
            event_count=row["event_count"],
            income_movement_count=row["income_movement_count"],
            expense_movement_count=row["expense_movement_count"],
        )
