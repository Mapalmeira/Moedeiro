import time
from collections.abc import Callable
from functools import partial
from uuid import UUID

from fastapi import HTTPException, Request, status

from app.application.ledger.exceptions import LedgerNotFoundError
from app.application.ledger.unit_of_work import LedgerUnitOfWork
from app.application.ledger.use_cases.ledger import access_owned_ledger


def ledger_unit_of_work_factory(request: Request, user_uuid: UUID, ledger_uuid: UUID) -> Callable[[], LedgerUnitOfWork]:
    try:
        ledger = access_owned_ledger(request.app.state.databases.open_registry, user_uuid, ledger_uuid, int(time.time()))
    except LedgerNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ledger not found") from error
    return partial(request.app.state.databases.open_ledger, ledger.path)
