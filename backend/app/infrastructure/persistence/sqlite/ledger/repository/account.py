import sqlite3
from uuid import UUID, uuid4

from app.domain.ledger.model.account import Account
from app.domain.ledger.repository.account import AccountRepository


class SqliteAccountRepository(AccountRepository):
    _SORT_COLUMNS = {
        "name": "account_name",
        "note": "note",
    }

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, name: str, note: str | None, currency_uuid: UUID, icon: str, color_code: bytes) -> Account:
        account = Account(uuid=uuid4(), name=name, note=note, currency_uuid=currency_uuid, icon=icon, color_code=color_code)
        self.connection.execute(
            "INSERT INTO account(uuid, account_name, note, currency_uuid, icon, color_code) VALUES (?, ?, ?, ?, ?, ?)",
            (account.uuid.bytes, account.name, account.note, account.currency_uuid.bytes, account.icon, account.color_code),
        )
        return account

    def get(self, uuid: UUID) -> Account | None:
        row = self.connection.execute(
            "SELECT uuid, account_name AS name, note, currency_uuid, icon, color_code FROM account WHERE uuid = ?",
            (uuid.bytes,),
        ).fetchone()
        if row is None:
            return None
        return self._to_model(row)

    def update_name(self, uuid: UUID, value: str) -> None:
        account = self._updated_model(uuid, name=value)
        if account is None:
            return
        self.connection.execute(
            "UPDATE account SET account_name = ? WHERE uuid = ?",
            (account.name, account.uuid.bytes),
        )

    def update_note(self, uuid: UUID, value: str | None) -> None:
        account = self._updated_model(uuid, note=value)
        if account is None:
            return
        self.connection.execute(
            "UPDATE account SET note = ? WHERE uuid = ?",
            (account.note, account.uuid.bytes),
        )

    def update_icon(self, uuid: UUID, value: str) -> None:
        account = self._updated_model(uuid, icon=value)
        if account is None:
            return
        self.connection.execute(
            "UPDATE account SET icon = ? WHERE uuid = ?",
            (account.icon, account.uuid.bytes),
        )

    def update_color_code(self, uuid: UUID, value: bytes) -> None:
        account = self._updated_model(uuid, color_code=value)
        if account is None:
            return
        self.connection.execute(
            "UPDATE account SET color_code = ? WHERE uuid = ?",
            (account.color_code, account.uuid.bytes),
        )

    def list_all(self) -> list[Account]:
        rows = self.connection.execute(
            "SELECT uuid, account_name AS name, note, currency_uuid, icon, color_code FROM account"
        ).fetchall()
        return [self._to_model(row) for row in rows]

    def list_page(self, page_number: int, page_size: int, sort_key: str, ascending: bool) -> list[Account]:
        self._validate_page(page_number, page_size)
        sort_column = self._get_sort_column(sort_key)
        direction = "ASC" if ascending else "DESC"
        offset = (page_number - 1) * page_size
        rows = self.connection.execute(
            f"""
            SELECT uuid, account_name AS name, note, currency_uuid, icon, color_code
            FROM account
            ORDER BY {sort_column} {direction}, uuid ASC
            LIMIT ? OFFSET ?
            """,
            (page_size, offset),
        ).fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: sqlite3.Row) -> Account:
        return Account.model_validate(dict(row))

    def _updated_model(self, uuid: UUID, **changes: object) -> Account | None:
        account = self.get(uuid)
        if account is None:
            return None
        return Account.model_validate({**account.model_dump(), **changes})

    @classmethod
    def _get_sort_column(cls, sort_key: str) -> str:
        try:
            return cls._SORT_COLUMNS[sort_key]
        except KeyError as error:
            raise ValueError(f"Invalid account sort key: {sort_key}") from error

    @staticmethod
    def _validate_page(page_number: int, page_size: int) -> None:
        if page_number < 1:
            raise ValueError("page_number must be greater than or equal to 1")
        if page_size < 1:
            raise ValueError("page_size must be greater than or equal to 1")
