import sqlite3

from app.application.ledger.exceptions import QueryResultOverflowError


def raise_query_result_overflow(error: sqlite3.OperationalError) -> None:
    if str(error) == "integer overflow":
        raise QueryResultOverflowError from error
    raise error


def require_sqlite_integer(value: int | float) -> int:
    # SQLite promotes an overflowing multiplication to REAL rather than failing.
    if not isinstance(value, int):
        raise QueryResultOverflowError
    return value
