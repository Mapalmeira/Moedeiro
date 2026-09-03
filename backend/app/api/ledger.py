import time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.authentication import require_authenticated_user
from app.api.schema.ledger import CreateLedgerRequest, LedgerResponse, UpdateLedgerRequest
from app.application.ledger.exceptions import LedgerNotFoundError
from app.application.ledger.use_cases.ledger import create_ledger, delete_owned_ledger, get_owned_ledger, list_owned_ledgers, update_owned_ledger
from app.application.registry.exceptions import UserNotFoundError
from app.domain.registry.model.user import User
from app.infrastructure.persistence.sqlite.ledger.schema_version import CURRENT_LEDGER_SCHEMA_VERSION


router = APIRouter(prefix="/api/ledgers", tags=["ledgers"])
AuthenticatedUser = Annotated[User, Depends(require_authenticated_user)]


@router.post("", response_model=LedgerResponse, status_code=status.HTTP_201_CREATED)
def create_owned_ledger(payload: CreateLedgerRequest, request: Request, user: AuthenticatedUser) -> LedgerResponse:
    databases = request.app.state.databases
    try:
        ledger = create_ledger(
            databases.open_registry,
            databases.initialize_ledger,
            databases.delete_ledger_database,
            user.uuid,
            payload.name,
            payload.icon,
            bytes.fromhex(payload.color_code[1:]),
            int(time.time()),
            CURRENT_LEDGER_SCHEMA_VERSION,
        )
    except UserNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session") from error
    return LedgerResponse.from_ledger(ledger)


@router.get("", response_model=list[LedgerResponse])
def list_user_ledgers(request: Request, user: AuthenticatedUser) -> list[LedgerResponse]:
    ledgers = list_owned_ledgers(request.app.state.databases.open_registry, user.uuid)
    return [LedgerResponse.from_ledger(ledger) for ledger in ledgers]


@router.get("/{ledger_uuid}", response_model=LedgerResponse)
def get_user_ledger(ledger_uuid: UUID, request: Request, user: AuthenticatedUser) -> LedgerResponse:
    try:
        ledger = get_owned_ledger(request.app.state.databases.open_registry, user.uuid, ledger_uuid)
    except LedgerNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ledger not found") from error
    return LedgerResponse.from_ledger(ledger)


@router.put("/{ledger_uuid}", response_model=LedgerResponse)
def update_user_ledger(
    ledger_uuid: UUID,
    payload: UpdateLedgerRequest,
    request: Request,
    user: AuthenticatedUser,
) -> LedgerResponse:
    try:
        ledger = update_owned_ledger(
            request.app.state.databases.open_registry,
            user.uuid,
            ledger_uuid,
            payload.name,
            payload.icon,
            bytes.fromhex(payload.color_code[1:]),
        )
    except LedgerNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ledger not found") from error
    return LedgerResponse.from_ledger(ledger)


@router.delete("/{ledger_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_ledger(ledger_uuid: UUID, request: Request, user: AuthenticatedUser) -> None:
    databases = request.app.state.databases
    try:
        delete_owned_ledger(
            databases.open_registry,
            databases.delete_ledger_database,
            user.uuid,
            ledger_uuid,
        )
    except LedgerNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ledger not found") from error
