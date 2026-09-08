from collections.abc import Callable
from uuid import UUID

from app.application.ledger.exceptions import AccountNotFoundError, BudgetLimitReachedError, BudgetNameUnavailableError, BudgetNotFoundError, CategoryNotFoundError
from app.application.ledger.unit_of_work import LedgerUnitOfWork
from app.domain.ledger.limits import MAXIMUM_BUDGETS
from app.domain.ledger.model.budget import Budget, BudgetAmount, BudgetDescription, BudgetName


def create_budget(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    account_uuid: UUID,
    category_uuid: UUID,
    from_timestamp: int,
    to_timestamp: int,
    name: BudgetName,
    description: BudgetDescription | None,
    amount: BudgetAmount,
) -> Budget:
    with unit_of_work_factory() as unit_of_work:
        if unit_of_work.budget_repository.count() >= MAXIMUM_BUDGETS:
            raise BudgetLimitReachedError
        _require_account(unit_of_work, account_uuid)
        _require_category(unit_of_work, category_uuid)
        if unit_of_work.budget_repository.get_by_name(name) is not None:
            raise BudgetNameUnavailableError
        budget = unit_of_work.budget_repository.create(
            account_uuid,
            category_uuid,
            from_timestamp,
            to_timestamp,
            name,
            description,
            amount,
        )
        unit_of_work.commit()
    return budget


def get_budget(unit_of_work_factory: Callable[[], LedgerUnitOfWork], budget_uuid: UUID) -> Budget:
    with unit_of_work_factory() as unit_of_work:
        budget = unit_of_work.budget_repository.get(budget_uuid)
        if budget is None:
            raise BudgetNotFoundError
        return budget


def update_budget(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    budget_uuid: UUID,
    category_uuid: UUID,
    from_timestamp: int,
    to_timestamp: int,
    name: BudgetName,
    description: BudgetDescription | None,
    amount: BudgetAmount,
) -> Budget:
    with unit_of_work_factory() as unit_of_work:
        budget = unit_of_work.budget_repository.get(budget_uuid)
        if budget is None:
            raise BudgetNotFoundError
        _require_category(unit_of_work, category_uuid)
        updated_budget = Budget.model_validate(
            {
                **budget.model_dump(),
                "category_uuid": category_uuid,
                "from_timestamp": from_timestamp,
                "to_timestamp": to_timestamp,
                "name": name,
                "description": description,
                "amount": amount,
            }
        )
        budget_with_name = unit_of_work.budget_repository.get_by_name(updated_budget.name)
        if budget_with_name is not None and budget_with_name.uuid != budget.uuid:
            raise BudgetNameUnavailableError
        unit_of_work.budget_repository.update(updated_budget)
        unit_of_work.commit()
    return updated_budget


def delete_budget(unit_of_work_factory: Callable[[], LedgerUnitOfWork], budget_uuid: UUID) -> None:
    with unit_of_work_factory() as unit_of_work:
        if unit_of_work.budget_repository.get(budget_uuid) is None:
            raise BudgetNotFoundError
        unit_of_work.budget_repository.delete(budget_uuid)
        unit_of_work.commit()


def _require_account(unit_of_work: LedgerUnitOfWork, account_uuid: UUID) -> None:
    if unit_of_work.account_repository.get(account_uuid) is None:
        raise AccountNotFoundError


def _require_category(unit_of_work: LedgerUnitOfWork, category_uuid: UUID) -> None:
    if unit_of_work.category_repository.get(category_uuid) is None:
        raise CategoryNotFoundError
