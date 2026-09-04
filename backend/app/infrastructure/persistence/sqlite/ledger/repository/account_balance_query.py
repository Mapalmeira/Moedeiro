import sqlite3
from uuid import UUID

from app.domain.ledger.repository.account_balance_query import AccountBalanceQueryRepository


class SqliteAccountBalanceQueryRepository(AccountBalanceQueryRepository):
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def get_balance_at(self, account_uuid: UUID, timestamp: int) -> int:
        self._ensure_account_exists(account_uuid)
        row = self.connection.execute(
            """
            SELECT COALESCE(SUM(movement.value * movement.quantity), 0) AS balance
            FROM financial_movement AS movement
            JOIN financial_event AS event ON event.uuid = movement.financial_event_uuid
            WHERE movement.account_uuid = ? AND event.occurred_at <= ?
            """,
            (account_uuid.bytes, timestamp),
        ).fetchone()
        return row["balance"]

    def list_points(self, account_uuid: UUID, from_timestamp: int, point_count: int, point_interval: int) -> list[int]:
        self._validate_point_parameters(point_count, point_interval)
        self._ensure_account_exists(account_uuid)
        to_timestamp = from_timestamp + point_count * point_interval
        rows = self.connection.execute(
            """
            SELECT
                CASE
                    WHEN event.occurred_at < ? THEN NULL
                    ELSE ? + ((event.occurred_at - ?) / ?) * ?
                END AS point_start,
                SUM(movement.value * movement.quantity) AS value
            FROM financial_movement AS movement
            JOIN financial_event AS event ON event.uuid = movement.financial_event_uuid
            WHERE movement.account_uuid = ?
              AND event.occurred_at < ?
            GROUP BY point_start
            """,
            (from_timestamp, from_timestamp, from_timestamp, point_interval, point_interval, account_uuid.bytes, to_timestamp),
        ).fetchall()
        changes = {row["point_start"]: row["value"] for row in rows if row["point_start"] is not None}
        balance = next((row["value"] for row in rows if row["point_start"] is None), 0)
        points: list[int] = []
        for point_start in range(from_timestamp, to_timestamp, point_interval):
            balance += changes.get(point_start, 0)
            points.append(balance)
        return points

    def _ensure_account_exists(self, account_uuid: UUID) -> None:
        row = self.connection.execute(
            "SELECT 1 FROM account WHERE uuid = ?",
            (account_uuid.bytes,),
        ).fetchone()
        if row is None:
            raise LookupError(f"account {account_uuid} does not exist")

    @staticmethod
    def _validate_point_parameters(point_count: int, point_interval: int) -> None:
        if point_count < 1:
            raise ValueError("point_count must be greater than zero")
        if point_interval < 1:
            raise ValueError("point_interval must be greater than zero")
