import sqlite3
from uuid import UUID

from app.domain.ledger.repository.account_balance_query import AccountBalanceQueryRepository


class SqliteAccountBalanceQueryRepository(AccountBalanceQueryRepository):
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def get_balance_at(self, account_uuid: UUID, timestamp: int) -> int:
        row = self.connection.execute(
            """
            SELECT COALESCE(SUM(movement.value), 0) AS balance
            FROM financial_movement AS movement
            JOIN transaction_event AS event ON event.uuid = movement.transaction_event_uuid
            WHERE movement.account_uuid = ? AND event.occurred_at <= ?
            """,
            (str(account_uuid), timestamp),
        ).fetchone()
        return row["balance"]
