import time
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from app.api.dependencies.authentication import AuthenticatedUser
from app.api.registry.schema.ledger import CreateLedgerRequest, LedgerResponse, LedgerSortKey, UpdateLedgerRequest
from app.application.ledger.exceptions import LedgerNotFoundError
from app.application.ledger.use_cases.ledger import access_owned_ledger, create_ledger, delete_owned_ledger, list_owned_ledgers, update_owned_ledger
from app.application.registry.exceptions import UserNotFoundError
from app.infrastructure.persistence.sqlite.ledger.schema_version import CURRENT_LEDGER_SCHEMA_VERSION


router = APIRouter(prefix="/api/ledgers", tags=["ledgers"])


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
def list_user_ledgers(request: Request, user: AuthenticatedUser, sort_key: LedgerSortKey = "last_accessed_at", ascending: bool = False) -> list[LedgerResponse]:
    ledgers = list_owned_ledgers(request.app.state.databases.open_registry, user.uuid, sort_key, ascending)
    return [LedgerResponse.from_ledger(ledger) for ledger in ledgers]


@router.get("/{ledger_uuid}", response_model=LedgerResponse)
def get_user_ledger(ledger_uuid: UUID, request: Request, user: AuthenticatedUser) -> LedgerResponse:
    try:
        ledger = access_owned_ledger(request.app.state.databases.open_registry, user.uuid, ledger_uuid, int(time.time()))
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
            int(time.time()),
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
