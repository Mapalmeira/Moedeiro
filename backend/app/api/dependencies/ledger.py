import time
from collections.abc import Callable
from functools import partial
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status

from app.api.dependencies.authentication import LedgerGrantee
from app.application.ledger.exceptions import LedgerNotFoundError
from app.application.ledger.unit_of_work import LedgerUnitOfWork
from app.application.ledger.use_cases.ledger import access_granted_ledger
from app.domain.registry.model.ledger import Ledger


def require_granted_ledger(request: Request, grantee: LedgerGrantee, ledger_uuid: UUID) -> Ledger:
    try:
        return access_granted_ledger(
            request.app.state.databases.open_registry,
            grantee.uuid,
            ledger_uuid,
            int(time.time()),
        )
    except LedgerNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ledger not found") from error


GrantedLedger = Annotated[Ledger, Depends(require_granted_ledger)]


def ledger_unit_of_work_factory(request: Request, ledger: Ledger) -> Callable[[], LedgerUnitOfWork]:
    return partial(request.app.state.databases.open_ledger, ledger.path)
