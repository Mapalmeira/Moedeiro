from collections.abc import Callable
from uuid import UUID

from app.application.ledger.exceptions import CurrencyInUseError, CurrencyLimitReachedError, CurrencyNameUnavailableError, CurrencyNotFoundError
from app.application.ledger.unit_of_work import LedgerUnitOfWork
from app.domain.appearance import Icon, RgbColorCode
from app.domain.ledger.limits import MAXIMUM_CURRENCIES
from app.domain.ledger.model.currency import Currency


def create_currency(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    name: str,
    prefix: str | None,
    suffix: str | None,
    decimal_places: int,
    icon: Icon,
    color_code: RgbColorCode,
) -> Currency:
    with unit_of_work_factory() as unit_of_work:
        if unit_of_work.currency_repository.count() >= MAXIMUM_CURRENCIES:
            raise CurrencyLimitReachedError
        if unit_of_work.currency_repository.get_by_name(name) is not None:
            raise CurrencyNameUnavailableError
        currency = unit_of_work.currency_repository.create(
            name,
            prefix,
            suffix,
            decimal_places,
            icon,
            color_code,
        )
        unit_of_work.commit()
    return currency


def get_currency(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    currency_uuid: UUID,
) -> Currency:
    with unit_of_work_factory() as unit_of_work:
        currency = unit_of_work.currency_repository.get(currency_uuid)
        if currency is None:
            raise CurrencyNotFoundError
        return currency


def list_currencies(unit_of_work_factory: Callable[[], LedgerUnitOfWork]) -> list[Currency]:
    with unit_of_work_factory() as unit_of_work:
        return unit_of_work.currency_repository.list_all()


def update_currency(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    currency_uuid: UUID,
    name: str,
    prefix: str | None,
    suffix: str | None,
    icon: Icon,
    color_code: RgbColorCode,
) -> Currency:
    with unit_of_work_factory() as unit_of_work:
        currency = unit_of_work.currency_repository.get(currency_uuid)
        if currency is None:
            raise CurrencyNotFoundError
        updated_currency = Currency.model_validate(
            {
                **currency.model_dump(),
                "name": name,
                "prefix": prefix,
                "suffix": suffix,
                "icon": icon,
                "color_code": color_code,
            }
        )
        currency_with_name = unit_of_work.currency_repository.get_by_name(updated_currency.name)
        if currency_with_name is not None and currency_with_name.uuid != currency.uuid:
            raise CurrencyNameUnavailableError
        unit_of_work.currency_repository.update_name(currency_uuid, updated_currency.name)
        unit_of_work.currency_repository.update_prefix(currency_uuid, updated_currency.prefix)
        unit_of_work.currency_repository.update_suffix(currency_uuid, updated_currency.suffix)
        unit_of_work.currency_repository.update_icon(currency_uuid, updated_currency.icon)
        unit_of_work.currency_repository.update_color_code(currency_uuid, updated_currency.color_code)
        unit_of_work.commit()
    return updated_currency


def delete_currency(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    currency_uuid: UUID,
) -> None:
    with unit_of_work_factory() as unit_of_work:
        if unit_of_work.currency_repository.get(currency_uuid) is None:
            raise CurrencyNotFoundError
        if unit_of_work.currency_repository.is_in_use(currency_uuid):
            raise CurrencyInUseError
        unit_of_work.currency_repository.delete(currency_uuid)
        unit_of_work.commit()
