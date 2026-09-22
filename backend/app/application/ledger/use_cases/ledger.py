from collections.abc import Callable
from pathlib import Path
from uuid import UUID, uuid4

from app.application.ledger.exceptions import LedgerNotFoundError
from app.application.registry.exceptions import LedgerLimitReachedError, UserNotFoundError
from app.application.registry.unit_of_work import RegistryUnitOfWork
from app.domain.appearance import Icon, RgbColorCode
from app.domain.registry.limits import MAXIMUM_LEDGERS_PER_USER
from app.domain.registry.model.ledger import Ledger, LedgerName
from app.domain.registry.model.user_preferences import Language


def create_ledger(
    unit_of_work_factory: Callable[[], RegistryUnitOfWork],
    initialize_database: Callable[[UUID, int, Language], Path],
    delete_database: Callable[[str | Path], None],
    user_uuid: UUID,
    name: LedgerName,
    icon: Icon,
    color_code: RgbColorCode,
    timestamp: int,
) -> Ledger:
    ledger_uuid = uuid4()
    database_path: Path | None = None
    try:
        with unit_of_work_factory() as unit_of_work:
            if unit_of_work.user_repository.get(user_uuid) is None:
                raise UserNotFoundError
            if unit_of_work.ledger_repository.count_owned_by_user(user_uuid) >= MAXIMUM_LEDGERS_PER_USER:
                raise LedgerLimitReachedError
            preferences = unit_of_work.user_preferences_repository.get(user_uuid)
            language: Language = "pt-BR" if preferences is None else preferences.language
            database_path = initialize_database(ledger_uuid, timestamp, language)
            ledger = unit_of_work.ledger_repository.create(
                ledger_uuid,
                name,
                database_path.name,
                icon,
                color_code,
                timestamp,
            )
            unit_of_work.ledger_grant_repository.create(user_uuid, ledger.uuid, "OWNER", timestamp)
            unit_of_work.commit()
    except Exception:
        if database_path is not None:
            delete_database(database_path)
        raise
    return ledger


def get_owned_ledger(
    unit_of_work_factory: Callable[[], RegistryUnitOfWork],
    user_uuid: UUID,
    ledger_uuid: UUID,
) -> Ledger:
    with unit_of_work_factory() as unit_of_work:
        return _get_owned_ledger(unit_of_work, user_uuid, ledger_uuid)


def access_owned_ledger(
    unit_of_work_factory: Callable[[], RegistryUnitOfWork],
    user_uuid: UUID,
    ledger_uuid: UUID,
    timestamp: int,
) -> Ledger:
    with unit_of_work_factory() as unit_of_work:
        ledger = _get_owned_ledger(unit_of_work, user_uuid, ledger_uuid)
        unit_of_work.ledger_repository.update_last_accessed_at(ledger.uuid, timestamp)
        unit_of_work.commit()
    return ledger.model_copy(update={"last_accessed_at": max(ledger.last_accessed_at, timestamp)})


def list_owned_ledgers(
    unit_of_work_factory: Callable[[], RegistryUnitOfWork],
    user_uuid: UUID,
    sort_key: str,
    ascending: bool,
) -> list[Ledger]:
    with unit_of_work_factory() as unit_of_work:
        return unit_of_work.ledger_repository.list_owned_by_user(user_uuid, sort_key, ascending)


def update_owned_ledger(
    unit_of_work_factory: Callable[[], RegistryUnitOfWork],
    user_uuid: UUID,
    ledger_uuid: UUID,
    name: LedgerName,
    icon: Icon,
    color_code: RgbColorCode,
    timestamp: int,
) -> Ledger:
    with unit_of_work_factory() as unit_of_work:
        ledger = _get_owned_ledger(unit_of_work, user_uuid, ledger_uuid)
        unit_of_work.ledger_repository.update_name(ledger.uuid, name)
        unit_of_work.ledger_repository.update_icon(ledger.uuid, icon)
        unit_of_work.ledger_repository.update_color_code(ledger.uuid, color_code)
        unit_of_work.ledger_repository.update_last_accessed_at(ledger.uuid, timestamp)
        unit_of_work.commit()
    return ledger.model_copy(update={"name": name, "icon": icon, "color_code": color_code, "last_accessed_at": max(ledger.last_accessed_at, timestamp)})


def delete_owned_ledger(
    unit_of_work_factory: Callable[[], RegistryUnitOfWork],
    delete_database: Callable[[str | Path], None],
    user_uuid: UUID,
    ledger_uuid: UUID,
) -> None:
    with unit_of_work_factory() as unit_of_work:
        ledger = _get_owned_ledger(unit_of_work, user_uuid, ledger_uuid)
        unit_of_work.ledger_repository.delete(ledger.uuid)
        unit_of_work.commit()
    delete_database(ledger.path)


def _get_owned_ledger(
    unit_of_work: RegistryUnitOfWork,
    user_uuid: UUID,
    ledger_uuid: UUID,
) -> Ledger:
    grant = unit_of_work.ledger_grant_repository.get_active_owner_by_ledger(ledger_uuid)
    if grant is None or grant.grantee_uuid != user_uuid:
        raise LedgerNotFoundError
    ledger = unit_of_work.ledger_repository.get(ledger_uuid)
    if ledger is None:
        raise LedgerNotFoundError
    return ledger
