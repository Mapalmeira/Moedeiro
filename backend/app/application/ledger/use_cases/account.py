from collections.abc import Callable
from uuid import UUID

from app.application.ledger.exceptions import AccountInUseError, AccountLimitReachedError, AccountNameUnavailableError, AccountNotFoundError, CurrencyNotFoundError
from app.application.ledger.unit_of_work import LedgerUnitOfWork
from app.domain.appearance import Icon, RgbColorCode
from app.domain.ledger.limits import MAXIMUM_ACCOUNTS
from app.domain.ledger.model.account import Account, AccountName, AccountNote


def create_account(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    name: AccountName,
    note: AccountNote | None,
    currency_uuid: UUID,
    icon: Icon,
    color_code: RgbColorCode,
) -> Account:
    with unit_of_work_factory() as unit_of_work:
        if unit_of_work.account_repository.count() >= MAXIMUM_ACCOUNTS:
            raise AccountLimitReachedError
        if unit_of_work.currency_repository.get(currency_uuid) is None:
            raise CurrencyNotFoundError
        if unit_of_work.account_repository.get_by_name(name) is not None:
            raise AccountNameUnavailableError
        account = unit_of_work.account_repository.create(name, note, currency_uuid, icon, color_code)
        unit_of_work.commit()
    return account


def get_account(unit_of_work_factory: Callable[[], LedgerUnitOfWork], account_uuid: UUID) -> Account:
    with unit_of_work_factory() as unit_of_work:
        account = unit_of_work.account_repository.get(account_uuid)
        if account is None:
            raise AccountNotFoundError
        return account


def list_accounts(unit_of_work_factory: Callable[[], LedgerUnitOfWork]) -> list[Account]:
    with unit_of_work_factory() as unit_of_work:
        return unit_of_work.account_repository.list_all()


def update_account(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    account_uuid: UUID,
    name: AccountName,
    note: AccountNote | None,
    icon: Icon,
    color_code: RgbColorCode,
) -> Account:
    with unit_of_work_factory() as unit_of_work:
        account = unit_of_work.account_repository.get(account_uuid)
        if account is None:
            raise AccountNotFoundError
        updated_account = Account.model_validate({**account.model_dump(), "name": name, "note": note, "icon": icon, "color_code": color_code})
        account_with_name = unit_of_work.account_repository.get_by_name(updated_account.name)
        if account_with_name is not None and account_with_name.uuid != account.uuid:
            raise AccountNameUnavailableError
        unit_of_work.account_repository.update_name(account.uuid, updated_account.name)
        unit_of_work.account_repository.update_note(account.uuid, updated_account.note)
        unit_of_work.account_repository.update_icon(account.uuid, updated_account.icon)
        unit_of_work.account_repository.update_color_code(account.uuid, updated_account.color_code)
        unit_of_work.commit()
    return updated_account


def delete_account(unit_of_work_factory: Callable[[], LedgerUnitOfWork], account_uuid: UUID) -> None:
    with unit_of_work_factory() as unit_of_work:
        if unit_of_work.account_repository.get(account_uuid) is None:
            raise AccountNotFoundError
        if unit_of_work.account_repository.is_in_use(account_uuid):
            raise AccountInUseError
        unit_of_work.account_repository.delete(account_uuid)
        unit_of_work.commit()
