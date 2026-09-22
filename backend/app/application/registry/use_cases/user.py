from collections.abc import Callable
from uuid import UUID

from pydantic import TypeAdapter

from app.application.registry.exceptions import UserNameUnavailableError, UserNotFoundError
from app.application.registry.password_hasher import PasswordHasher
from app.application.registry.unit_of_work import RegistryUnitOfWork
from app.domain.registry.model.ledger import Ledger
from app.domain.registry.model.user import Password, User, UserName, normalize_user_name


_password_adapter = TypeAdapter(Password)


def create_user(unit_of_work_factory: Callable[[], RegistryUnitOfWork], password_hasher: PasswordHasher, name: UserName, password: Password, timestamp: int) -> User:
    password = _password_adapter.validate_python(password)
    password_hash = password_hasher.hash(password)
    with unit_of_work_factory() as unit_of_work:
        if unit_of_work.user_repository.get_by_normalized_name(normalize_user_name(name)) is not None:
            raise UserNameUnavailableError
        user = unit_of_work.user_repository.create(name, password_hash, timestamp)
        unit_of_work.commit()
    return user


def list_users(unit_of_work_factory: Callable[[], RegistryUnitOfWork], sort_key: str, ascending: bool) -> list[User]:
    with unit_of_work_factory() as unit_of_work:
        return unit_of_work.user_repository.list_all(sort_key, ascending)


def delete_user(unit_of_work_factory: Callable[[], RegistryUnitOfWork], user_uuid: UUID) -> list[Ledger]:
    with unit_of_work_factory() as unit_of_work:
        if unit_of_work.user_repository.get(user_uuid) is None:
            raise UserNotFoundError
        ledgers: list[Ledger] = []
        for grant in unit_of_work.ledger_grant_repository.list_by_user(user_uuid):
            if grant.type != "OWNER" or grant.revoked_at is not None:
                continue
            ledger = unit_of_work.ledger_repository.get(grant.ledger_uuid)
            if ledger is not None:
                ledgers.append(ledger)
        for ledger in ledgers:
            unit_of_work.ledger_repository.delete(ledger.uuid)
        unit_of_work.user_repository.delete(user_uuid)
        unit_of_work.commit()
    return ledgers
