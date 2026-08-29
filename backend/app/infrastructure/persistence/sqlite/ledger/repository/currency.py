import sqlite3
from uuid import UUID, uuid4

from app.domain.ledger.model.currency import Currency
from app.domain.ledger.repository.currency import CurrencyRepository


class SqliteCurrencyRepository(CurrencyRepository):
    _SORT_COLUMNS = {
        "name": "currency_name",
        "prefix": "prefix",
        "suffix": "suffix",
        "decimal_places": "decimal_places",
    }

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, name: str, prefix: str | None, suffix: str | None, decimal_places: int, icon: str, color_code: bytes) -> Currency:
        currency = Currency(uuid=uuid4(), name=name, prefix=prefix, suffix=suffix, decimal_places=decimal_places, icon=icon, color_code=color_code)
        self.connection.execute(
            "INSERT INTO currency(uuid, currency_name, prefix, suffix, decimal_places, icon, color_code) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (currency.uuid.bytes, currency.name, currency.prefix, currency.suffix, currency.decimal_places, currency.icon, currency.color_code),
        )
        return currency

    def get(self, uuid: UUID) -> Currency | None:
        row = self.connection.execute(
            "SELECT uuid, currency_name AS name, prefix, suffix, decimal_places, icon, color_code FROM currency WHERE uuid = ?",
            (uuid.bytes,),
        ).fetchone()
        if row is None:
            return None
        return self._to_model(row)

    def update_name(self, uuid: UUID, value: str) -> None:
        currency = self._updated_model(uuid, name=value)
        if currency is None:
            return
        self.connection.execute(
            "UPDATE currency SET currency_name = ? WHERE uuid = ?",
            (currency.name, currency.uuid.bytes),
        )

    def update_prefix(self, uuid: UUID, value: str | None) -> None:
        currency = self._updated_model(uuid, prefix=value)
        if currency is None:
            return
        self.connection.execute(
            "UPDATE currency SET prefix = ? WHERE uuid = ?",
            (currency.prefix, currency.uuid.bytes),
        )

    def update_suffix(self, uuid: UUID, value: str | None) -> None:
        currency = self._updated_model(uuid, suffix=value)
        if currency is None:
            return
        self.connection.execute(
            "UPDATE currency SET suffix = ? WHERE uuid = ?",
            (currency.suffix, currency.uuid.bytes),
        )

    def update_icon(self, uuid: UUID, value: str) -> None:
        currency = self._updated_model(uuid, icon=value)
        if currency is None:
            return
        self.connection.execute(
            "UPDATE currency SET icon = ? WHERE uuid = ?",
            (currency.icon, currency.uuid.bytes),
        )

    def update_color_code(self, uuid: UUID, value: bytes) -> None:
        currency = self._updated_model(uuid, color_code=value)
        if currency is None:
            return
        self.connection.execute(
            "UPDATE currency SET color_code = ? WHERE uuid = ?",
            (currency.color_code, currency.uuid.bytes),
        )

    def list_all(self) -> list[Currency]:
        rows = self.connection.execute(
            "SELECT uuid, currency_name AS name, prefix, suffix, decimal_places, icon, color_code FROM currency"
        ).fetchall()
        return [self._to_model(row) for row in rows]

    def list_page(self, page_number: int, page_size: int, sort_key: str, ascending: bool) -> list[Currency]:
        self._validate_page(page_number, page_size)
        sort_column = self._get_sort_column(sort_key)
        direction = "ASC" if ascending else "DESC"
        offset = (page_number - 1) * page_size
        rows = self.connection.execute(
            f"""
            SELECT uuid, currency_name AS name, prefix, suffix, decimal_places, icon, color_code
            FROM currency
            ORDER BY {sort_column} {direction}, uuid ASC
            LIMIT ? OFFSET ?
            """,
            (page_size, offset),
        ).fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: sqlite3.Row) -> Currency:
        return Currency.model_validate(dict(row))

    def _updated_model(self, uuid: UUID, **changes: object) -> Currency | None:
        currency = self.get(uuid)
        if currency is None:
            return None
        return Currency.model_validate({**currency.model_dump(), **changes})

    @classmethod
    def _get_sort_column(cls, sort_key: str) -> str:
        try:
            return cls._SORT_COLUMNS[sort_key]
        except KeyError as error:
            raise ValueError(f"Invalid currency sort key: {sort_key}") from error

    @staticmethod
    def _validate_page(page_number: int, page_size: int) -> None:
        if page_number < 1:
            raise ValueError("page_number must be greater than or equal to 1")
        if page_size < 1:
            raise ValueError("page_size must be greater than or equal to 1")
