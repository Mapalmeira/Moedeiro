from collections.abc import Callable, Collection
from uuid import UUID

from app.application.ledger.exceptions import AccountNotFoundError, BudgetAccountCurrencyMismatchError, BudgetNameUnavailableError, BudgetNotFoundError, CategoryNotFoundError, CurrencyNotFoundError
from app.application.ledger.unit_of_work import LedgerUnitOfWork
from app.domain.appearance import Icon, RgbColorCode
from app.domain.ledger.model.budget import Budget, BudgetAmount, BudgetDescription, BudgetName


def create_budget(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    category_uuid: UUID,
    currency_uuid: UUID,
    from_timestamp: int,
    to_timestamp: int,
    name: BudgetName,
    description: BudgetDescription,
    amount: BudgetAmount,
    icon: Icon,
    color_code: RgbColorCode,
    account_uuids: Collection[UUID],
) -> Budget:
    with unit_of_work_factory() as unit_of_work:
        _require_currency(unit_of_work, currency_uuid)
        _require_category(unit_of_work, category_uuid)
        selected_account_uuids = _require_accounts_in_currency(unit_of_work, account_uuids, currency_uuid)
        if unit_of_work.budget_repository.get_by_name(name) is not None:
            raise BudgetNameUnavailableError
        budget = unit_of_work.budget_repository.create(category_uuid, currency_uuid, from_timestamp, to_timestamp, name, description, amount, icon, color_code)
        for account_uuid in selected_account_uuids:
            unit_of_work.budget_repository.add_account(budget.uuid, account_uuid)
        budget = Budget.model_validate({**budget.model_dump(), "account_uuids": selected_account_uuids})
        unit_of_work.commit()
    return budget


def get_budget(unit_of_work_factory: Callable[[], LedgerUnitOfWork], budget_uuid: UUID) -> Budget:
    with unit_of_work_factory() as unit_of_work:
        budget = unit_of_work.budget_repository.get(budget_uuid)
        if budget is None:
            raise BudgetNotFoundError
        return budget


def list_budget_page(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    page_number: int,
    page_size: int,
    sort_key: str,
    ascending: bool,
) -> list[Budget]:
    with unit_of_work_factory() as unit_of_work:
        return unit_of_work.budget_repository.list_page(page_number, page_size, sort_key, ascending)


def update_budget(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    budget_uuid: UUID,
    category_uuid: UUID,
    from_timestamp: int,
    to_timestamp: int,
    name: BudgetName,
    description: BudgetDescription,
    amount: BudgetAmount,
    icon: Icon,
    color_code: RgbColorCode,
    account_uuids: Collection[UUID],
) -> Budget:
    with unit_of_work_factory() as unit_of_work:
        budget = unit_of_work.budget_repository.get(budget_uuid)
        if budget is None:
            raise BudgetNotFoundError
        _require_category(unit_of_work, category_uuid)
        selected_account_uuids = _require_accounts_in_currency(unit_of_work, account_uuids, budget.currency_uuid)
        updated_budget = Budget.model_validate(
            {
                **budget.model_dump(),
                "category_uuid": category_uuid,
                "from_timestamp": from_timestamp,
                "to_timestamp": to_timestamp,
                "name": name,
                "description": description,
                "amount": amount,
                "icon": icon,
                "color_code": color_code,
                "account_uuids": selected_account_uuids,
            }
        )
        budget_with_name = unit_of_work.budget_repository.get_by_name(updated_budget.name)
        if budget_with_name is not None and budget_with_name.uuid != budget.uuid:
            raise BudgetNameUnavailableError
        unit_of_work.budget_repository.update_period(budget.uuid, updated_budget.from_timestamp, updated_budget.to_timestamp)
        unit_of_work.budget_repository.update_name(budget.uuid, updated_budget.name)
        unit_of_work.budget_repository.update_description(budget.uuid, updated_budget.description)
        unit_of_work.budget_repository.update_amount(budget.uuid, updated_budget.amount)
        unit_of_work.budget_repository.update_category(budget.uuid, updated_budget.category_uuid)
        unit_of_work.budget_repository.update_icon(budget.uuid, updated_budget.icon)
        unit_of_work.budget_repository.update_color_code(budget.uuid, updated_budget.color_code)
        existing_account_uuids = set(budget.account_uuids)
        requested_account_uuids = set(updated_budget.account_uuids)
        for account_uuid in existing_account_uuids - requested_account_uuids:
            unit_of_work.budget_repository.remove_account(budget.uuid, account_uuid)
        for account_uuid in requested_account_uuids - existing_account_uuids:
            unit_of_work.budget_repository.add_account(budget.uuid, account_uuid)
        unit_of_work.commit()
    return updated_budget


def delete_budget(unit_of_work_factory: Callable[[], LedgerUnitOfWork], budget_uuid: UUID) -> None:
    with unit_of_work_factory() as unit_of_work:
        if unit_of_work.budget_repository.get(budget_uuid) is None:
            raise BudgetNotFoundError
        unit_of_work.budget_repository.delete(budget_uuid)
        unit_of_work.commit()


def _require_currency(unit_of_work: LedgerUnitOfWork, currency_uuid: UUID) -> None:
    if unit_of_work.currency_repository.get(currency_uuid) is None:
        raise CurrencyNotFoundError


def _require_category(unit_of_work: LedgerUnitOfWork, category_uuid: UUID) -> None:
    if unit_of_work.category_repository.get(category_uuid) is None:
        raise CategoryNotFoundError


def _require_accounts_in_currency(unit_of_work: LedgerUnitOfWork, account_uuids: Collection[UUID], currency_uuid: UUID) -> list[UUID]:
    selected_account_uuids = sorted(set(account_uuids), key=lambda value: value.bytes)
    for account_uuid in selected_account_uuids:
        account = unit_of_work.account_repository.get(account_uuid)
        if account is None:
            raise AccountNotFoundError
        if account.currency_uuid != currency_uuid:
            raise BudgetAccountCurrencyMismatchError
    return selected_account_uuids
