import sqlite3
from uuid import UUID

from app.domain.ledger.repository.account_balance_query import AccountBalanceQueryRepository


class SqliteAccountBalanceQueryRepository(AccountBalanceQueryRepository):
    _SECONDS_PER_DAY = 86400

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def get_balance_at(self, account_uuid: UUID, timestamp: int) -> int:
        self._ensure_account_exists(account_uuid)
        row = self.connection.execute(
            """
            SELECT COALESCE(SUM(movement.value), 0) AS balance
            FROM financial_movement AS movement
            JOIN transaction_event AS event ON event.uuid = movement.transaction_event_uuid
            WHERE movement.account_uuid = ? AND event.occurred_at <= ?
            """,
            (account_uuid.bytes, timestamp),
        ).fetchone()
        return row["balance"]

    def list_points(self, account_uuid: UUID, from_timestamp: int, to_timestamp: int) -> list[int]:
        self._validate_period(from_timestamp, to_timestamp)
        self._ensure_account_exists(account_uuid)
        opening_row = self.connection.execute(
            """
            SELECT COALESCE(SUM(movement.value), 0) AS balance
            FROM financial_movement AS movement
            JOIN transaction_event AS event ON event.uuid = movement.transaction_event_uuid
            WHERE movement.account_uuid = ? AND event.occurred_at < ?
            """,
            (account_uuid.bytes, from_timestamp),
        ).fetchone()
        change_rows = self.connection.execute(
            f"""
            SELECT
                ? + ((event.occurred_at - ?) / {self._SECONDS_PER_DAY}) * {self._SECONDS_PER_DAY} AS day_start,
                SUM(movement.value) AS balance_change
            FROM financial_movement AS movement
            JOIN transaction_event AS event ON event.uuid = movement.transaction_event_uuid
            WHERE movement.account_uuid = ?
              AND event.occurred_at >= ?
              AND event.occurred_at < ?
            GROUP BY day_start
            """,
            (from_timestamp, from_timestamp, account_uuid.bytes, from_timestamp, to_timestamp),
        ).fetchall()
        changes = {row["day_start"]: row["balance_change"] for row in change_rows}
        balance = opening_row["balance"]
        points: list[int] = []
        for day_start in range(from_timestamp, to_timestamp, self._SECONDS_PER_DAY):
            balance += changes.get(day_start, 0)
            points.append(balance)
        return points

    def _ensure_account_exists(self, account_uuid: UUID) -> None:
        row = self.connection.execute(
            "SELECT 1 FROM account WHERE uuid = ?",
            (account_uuid.bytes,),
        ).fetchone()
        if row is None:
            raise LookupError(f"account {account_uuid} does not exist")

    @classmethod
    def _validate_period(cls, from_timestamp: int, to_timestamp: int) -> None:
        if from_timestamp >= to_timestamp:
            raise ValueError("from_timestamp must be less than to_timestamp")
        if (to_timestamp - from_timestamp) % cls._SECONDS_PER_DAY != 0:
            raise ValueError("the interval must contain complete 24-hour days")
