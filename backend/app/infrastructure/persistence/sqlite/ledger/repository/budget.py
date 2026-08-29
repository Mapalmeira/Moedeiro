import sqlite3
from uuid import UUID, uuid4

from app.domain.ledger.model.account import Account
from app.domain.ledger.model.budget import Budget
from app.domain.ledger.repository.budget import BudgetRepository


class SqliteBudgetRepository(BudgetRepository):
    _SORT_COLUMNS = {
        "from_timestamp": "from_timestamp",
        "to_timestamp": "to_timestamp",
        "name": "budget_name",
        "description": "description",
        "amount": "amount",
    }

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, category_uuid: UUID, currency_uuid: UUID, from_timestamp: int, to_timestamp: int, name: str, description: str, amount: int) -> Budget:
        budget = Budget(
            uuid=uuid4(),
            category_uuid=category_uuid,
            currency_uuid=currency_uuid,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            name=name,
            description=description,
            amount=amount,
        )
        self.connection.execute(
            """
            INSERT INTO budget(uuid, category_uuid, currency_uuid, from_timestamp, to_timestamp, budget_name, description, amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(budget.uuid),
                str(budget.category_uuid),
                str(budget.currency_uuid),
                budget.from_timestamp,
                budget.to_timestamp,
                budget.name,
                budget.description,
                budget.amount,
            ),
        )
        return budget

    def get(self, uuid: UUID) -> Budget | None:
        row = self.connection.execute(
            """
            SELECT uuid, category_uuid, currency_uuid, from_timestamp, to_timestamp, budget_name AS name, description, amount
            FROM budget
            WHERE uuid = ?
            """,
            (str(uuid),),
        ).fetchone()
        if row is None:
            return None
        return self._to_model(row)

    def update_period(self, uuid: UUID, from_timestamp: int, to_timestamp: int) -> None:
        budget = self._validation_model(uuid, from_timestamp=from_timestamp, to_timestamp=to_timestamp)
        self.connection.execute(
            "UPDATE budget SET from_timestamp = ?, to_timestamp = ? WHERE uuid = ?",
            (budget.from_timestamp, budget.to_timestamp, str(budget.uuid)),
        )

    def update_name(self, uuid: UUID, value: str) -> None:
        budget = self._validation_model(uuid, name=value)
        self.connection.execute(
            "UPDATE budget SET budget_name = ? WHERE uuid = ?",
            (budget.name, str(budget.uuid)),
        )

    def update_description(self, uuid: UUID, value: str) -> None:
        budget = self._validation_model(uuid, description=value)
        self.connection.execute(
            "UPDATE budget SET description = ? WHERE uuid = ?",
            (budget.description, str(budget.uuid)),
        )

    def update_amount(self, uuid: UUID, value: int) -> None:
        budget = self._validation_model(uuid, amount=value)
        self.connection.execute(
            "UPDATE budget SET amount = ? WHERE uuid = ?",
            (budget.amount, str(budget.uuid)),
        )

    def update_category(self, uuid: UUID, category_uuid: UUID) -> None:
        budget = self._validation_model(uuid, category_uuid=category_uuid)
        self.connection.execute(
            "UPDATE budget SET category_uuid = ? WHERE uuid = ?",
            (str(budget.category_uuid), str(budget.uuid)),
        )

    def add_account(self, budget_uuid: UUID, account_uuid: UUID) -> None:
        self.connection.execute(
            """
            INSERT INTO budget_accounts(budget_uuid, account_uuid, currency_uuid)
            SELECT uuid, ?, currency_uuid FROM budget WHERE uuid = ?
            """,
            (str(account_uuid), str(budget_uuid)),
        )

    def remove_account(self, budget_uuid: UUID, account_uuid: UUID) -> None:
        self.connection.execute(
            "DELETE FROM budget_accounts WHERE budget_uuid = ? AND account_uuid = ?",
            (str(budget_uuid), str(account_uuid)),
        )

    def list_accounts(self, budget_uuid: UUID) -> list[Account]:
        rows = self.connection.execute(
            """
            SELECT account.uuid, account.account_name AS name, account.note, account.currency_uuid
            FROM account
            JOIN budget_accounts ON budget_accounts.account_uuid = account.uuid
            WHERE budget_accounts.budget_uuid = ?
            """,
            (str(budget_uuid),),
        ).fetchall()
        return [Account.model_validate(dict(row)) for row in rows]

    def list_all(self) -> list[Budget]:
        rows = self.connection.execute(
            """
            SELECT uuid, category_uuid, currency_uuid, from_timestamp, to_timestamp, budget_name AS name, description, amount
            FROM budget
            """
        ).fetchall()
        return [self._to_model(row) for row in rows]

    def list_page(self, page_number: int, page_size: int, sort_key: str, ascending: bool) -> list[Budget]:
        self._validate_page(page_number, page_size)
        sort_column = self._get_sort_column(sort_key)
        direction = "ASC" if ascending else "DESC"
        offset = (page_number - 1) * page_size
        rows = self.connection.execute(
            f"""
            SELECT uuid, category_uuid, currency_uuid, from_timestamp, to_timestamp, budget_name AS name, description, amount
            FROM budget
            ORDER BY {sort_column} {direction}, uuid ASC
            LIMIT ? OFFSET ?
            """,
            (page_size, offset),
        ).fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _validation_model(uuid: UUID, category_uuid: UUID | None = None, from_timestamp: int = 0, to_timestamp: int = 1, name: str = "budget", description: str = "budget", amount: int = 0) -> Budget:
        return Budget(
            uuid=uuid,
            category_uuid=category_uuid or uuid,
            currency_uuid=uuid,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            name=name,
            description=description,
            amount=amount,
        )

    @staticmethod
    def _to_model(row: sqlite3.Row) -> Budget:
        return Budget.model_validate(dict(row))

    @classmethod
    def _get_sort_column(cls, sort_key: str) -> str:
        try:
            return cls._SORT_COLUMNS[sort_key]
        except KeyError as error:
            raise ValueError(f"Invalid budget sort key: {sort_key}") from error

    @staticmethod
    def _validate_page(page_number: int, page_size: int) -> None:
        if page_number < 1:
            raise ValueError("page_number must be greater than or equal to 1")
        if page_size < 1:
            raise ValueError("page_size must be greater than or equal to 1")
