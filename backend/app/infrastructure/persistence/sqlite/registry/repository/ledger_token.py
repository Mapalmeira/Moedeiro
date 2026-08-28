import sqlite3
from uuid import UUID, uuid4

from app.domain.registry.model.ledger_token import LedgerToken
from app.domain.registry.repository.ledger_token import LedgerTokenRepository


class SqliteLedgerTokenRepository(LedgerTokenRepository):
    _SORT_COLUMNS = {
        "token_hash": "token_hash",
        "label": "label",
        "created_at": "created_at",
        "revoked_at": "revoked_at",
    }

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(
        self,
        ledger_uuid: UUID,
        token_hash: str,
        label: str | None,
        created_at: int,
    ) -> None:
        ledger_token = LedgerToken(
            uuid=uuid4(),
            ledger_uuid=ledger_uuid,
            token_hash=token_hash,
            label=label,
            created_at=created_at,
        )
        self.connection.execute(
            """
            INSERT INTO ledger_token(
                uuid,
                ledger_uuid,
                token_hash,
                label,
                created_at,
                revoked_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(ledger_token.uuid),
                str(ledger_token.ledger_uuid),
                ledger_token.token_hash,
                ledger_token.label,
                ledger_token.created_at,
                ledger_token.revoked_at,
            ),
        )

    def get(self, uuid: UUID) -> LedgerToken | None:
        row = self.connection.execute(
            """
            SELECT uuid, ledger_uuid, token_hash, label, created_at, revoked_at
            FROM ledger_token
            WHERE uuid = ?
            """,
            (str(uuid),),
        ).fetchone()
        if row is None:
            return None
        return self._to_model(row)

    def get_by_token_hash(self, token_hash: str) -> LedgerToken | None:
        row = self.connection.execute(
            """
            SELECT uuid, ledger_uuid, token_hash, label, created_at, revoked_at
            FROM ledger_token
            WHERE token_hash = ?
            """,
            (token_hash,),
        ).fetchone()
        if row is None:
            return None
        return self._to_model(row)

    def update_label(self, uuid: UUID, value: str | None) -> None:
        ledger_token = self.get(uuid)
        if ledger_token is None:
            return

        updated_token = LedgerToken(
            uuid=ledger_token.uuid,
            ledger_uuid=ledger_token.ledger_uuid,
            token_hash=ledger_token.token_hash,
            label=value,
            created_at=ledger_token.created_at,
            revoked_at=ledger_token.revoked_at,
        )
        self.connection.execute(
            "UPDATE ledger_token SET label = ? WHERE uuid = ?",
            (updated_token.label, str(updated_token.uuid)),
        )

    def revoke(self, uuid: UUID, revoked_at: int) -> None:
        self.connection.execute(
            """
            UPDATE ledger_token
            SET revoked_at = ?
            WHERE uuid = ? AND revoked_at IS NULL
            """,
            (revoked_at, str(uuid)),
        )

    def list_by_ledger(self, ledger_uuid: UUID) -> list[LedgerToken]:
        rows = self.connection.execute(
            """
            SELECT uuid, ledger_uuid, token_hash, label, created_at, revoked_at
            FROM ledger_token
            WHERE ledger_uuid = ?
            """,
            (str(ledger_uuid),),
        ).fetchall()
        return [self._to_model(row) for row in rows]

    def list_all(self) -> list[LedgerToken]:
        rows = self.connection.execute(
            """
            SELECT uuid, ledger_uuid, token_hash, label, created_at, revoked_at
            FROM ledger_token
            """
        ).fetchall()
        return [self._to_model(row) for row in rows]

    def list_page(
        self,
        page_number: int,
        page_size: int,
        sort_key: str,
        ascending: bool,
    ) -> list[LedgerToken]:
        self._validate_page(page_number, page_size)
        sort_column = self._get_sort_column(sort_key)
        direction = "ASC" if ascending else "DESC"
        offset = (page_number - 1) * page_size

        rows = self.connection.execute(
            f"""
            SELECT uuid, ledger_uuid, token_hash, label, created_at, revoked_at
            FROM ledger_token
            ORDER BY {sort_column} {direction}, uuid ASC
            LIMIT ? OFFSET ?
            """,
            (page_size, offset),
        ).fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: sqlite3.Row) -> LedgerToken:
        return LedgerToken.model_validate(dict(row))

    @classmethod
    def _get_sort_column(cls, sort_key: str) -> str:
        try:
            return cls._SORT_COLUMNS[sort_key]
        except KeyError as error:
            raise ValueError(f"Invalid ledger token sort key: {sort_key}") from error

    @staticmethod
    def _validate_page(page_number: int, page_size: int) -> None:
        if page_number < 1:
            raise ValueError("page_number must be greater than or equal to 1")
        if page_size < 1:
            raise ValueError("page_size must be greater than or equal to 1")
