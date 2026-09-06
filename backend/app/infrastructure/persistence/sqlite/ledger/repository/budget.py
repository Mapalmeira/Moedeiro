import sqlite3
from uuid import UUID, uuid4

from app.domain.appearance import Icon, RgbColorCode
from app.domain.ledger.model.budget import Budget, BudgetAmount, BudgetDescription, BudgetName
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

    def create(self, category_uuid: UUID, currency_uuid: UUID, from_timestamp: int, to_timestamp: int, name: BudgetName, description: BudgetDescription, amount: BudgetAmount, icon: Icon, color_code: RgbColorCode) -> Budget:
        budget = Budget(
            uuid=uuid4(),
            category_uuid=category_uuid,
            currency_uuid=currency_uuid,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            name=name,
            description=description,
            amount=amount,
            icon=icon,
            color_code=color_code,
        )
        self.connection.execute(
            """
            INSERT INTO budget(uuid, category_uuid, currency_uuid, from_timestamp, to_timestamp, budget_name, description, amount, icon, color_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                budget.uuid.bytes,
                budget.category_uuid.bytes,
                budget.currency_uuid.bytes,
                budget.from_timestamp,
                budget.to_timestamp,
                budget.name,
                budget.description,
                budget.amount,
                budget.icon,
                budget.color_code,
            ),
        )
        return budget

    def get(self, uuid: UUID) -> Budget | None:
        row = self.connection.execute(
            """
            SELECT uuid, category_uuid, currency_uuid, from_timestamp, to_timestamp, budget_name AS name, description, amount, icon, color_code
            FROM budget
            WHERE uuid = ?
            """,
            (uuid.bytes,),
        ).fetchone()
        if row is None:
            return None
        return self._to_model(row, self._list_account_uuids([uuid])[uuid])

    def get_by_name(self, name: BudgetName) -> Budget | None:
        row = self.connection.execute(
            """
            SELECT uuid, category_uuid, currency_uuid, from_timestamp, to_timestamp, budget_name AS name, description, amount, icon, color_code
            FROM budget
            WHERE budget_name = ?
            """,
            (name,),
        ).fetchone()
        if row is None:
            return None
        uuid = UUID(bytes=row["uuid"])
        return self._to_model(row, self._list_account_uuids([uuid])[uuid])

    def update(self, budget: Budget) -> None:
        self.connection.execute(
            """
            UPDATE budget
            SET category_uuid = ?, from_timestamp = ?, to_timestamp = ?, budget_name = ?, description = ?, amount = ?, icon = ?, color_code = ?
            WHERE uuid = ?
            """,
            (
                budget.category_uuid.bytes,
                budget.from_timestamp,
                budget.to_timestamp,
                budget.name,
                budget.description,
                budget.amount,
                budget.icon,
                budget.color_code,
                budget.uuid.bytes,
            ),
        )

    def add_account(self, budget_uuid: UUID, account_uuid: UUID) -> None:
        self.connection.execute(
            """
            INSERT INTO budget_accounts(budget_uuid, account_uuid, currency_uuid)
            SELECT uuid, ?, currency_uuid FROM budget WHERE uuid = ?
            """,
            (account_uuid.bytes, budget_uuid.bytes),
        )

    def remove_account(self, budget_uuid: UUID, account_uuid: UUID) -> None:
        self.connection.execute(
            "DELETE FROM budget_accounts WHERE budget_uuid = ? AND account_uuid = ?",
            (budget_uuid.bytes, account_uuid.bytes),
        )

    def list_page(self, page_number: int, page_size: int, sort_key: str, ascending: bool) -> list[Budget]:
        sort_column = self._get_sort_column(sort_key)
        direction = "ASC" if ascending else "DESC"
        offset = (page_number - 1) * page_size
        rows = self.connection.execute(
            f"""
            SELECT uuid, category_uuid, currency_uuid, from_timestamp, to_timestamp, budget_name AS name, description, amount, icon, color_code
            FROM budget
            ORDER BY {sort_column} {direction}, uuid ASC
            LIMIT ? OFFSET ?
            """,
            (page_size, offset),
        ).fetchall()
        budget_uuids = [UUID(bytes=row["uuid"]) for row in rows]
        account_uuids = self._list_account_uuids(budget_uuids)
        return [self._to_model(row, account_uuids[UUID(bytes=row["uuid"])]) for row in rows]

    def count(self) -> int:
        return int(self.connection.execute("SELECT COUNT(*) FROM budget").fetchone()[0])

    def delete(self, uuid: UUID) -> None:
        self.connection.execute("DELETE FROM budget WHERE uuid = ?", (uuid.bytes,))

    def _list_account_uuids(self, budget_uuids: list[UUID]) -> dict[UUID, list[UUID]]:
        result = {budget_uuid: [] for budget_uuid in budget_uuids}
        if not budget_uuids:
            return result
        placeholders = ", ".join("?" for _ in budget_uuids)
        rows = self.connection.execute(
            f"SELECT budget_uuid, account_uuid FROM budget_accounts WHERE budget_uuid IN ({placeholders}) ORDER BY account_uuid ASC",
            [budget_uuid.bytes for budget_uuid in budget_uuids],
        ).fetchall()
        for row in rows:
            result[UUID(bytes=row["budget_uuid"])].append(UUID(bytes=row["account_uuid"]))
        return result

    @staticmethod
    def _to_model(row: sqlite3.Row, account_uuids: list[UUID]) -> Budget:
        return Budget.model_validate({**dict(row), "account_uuids": account_uuids})

    @classmethod
    def _get_sort_column(cls, sort_key: str) -> str:
        try:
            return cls._SORT_COLUMNS[sort_key]
        except KeyError as error:
            raise ValueError(f"Invalid budget sort key: {sort_key}") from error
