import time
from functools import partial
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api.dependencies.authentication import AuthenticatedUser
from app.api.dependencies.credential_operation import execute_credential_operation
from app.api.registry.schema.external_access import CreateExternalAccessRequest, CreatedExternalAccessGrantResponse, ExternalAccessGrantResponse, RevokeExternalAccessRequest
from app.application.registry.exceptions import InvalidCurrentPasswordError, InvalidTotpCodeError, LedgerGrantNotFoundError, LedgerNotFoundError, TotpCodeAlreadyUsedError, TotpRequiredError
from app.application.registry.use_cases.grant import create_external_ledger_grant, list_external_access_grants_for_owned_ledger, revoke_external_access_grant_from_owned_ledger


router = APIRouter(prefix="/api/ledgers/{ledger_uuid}/external-accesses", tags=["external access"])


@router.get("", response_model=list[ExternalAccessGrantResponse])
def list_ledger_external_accesses(ledger_uuid: UUID, request: Request, user: AuthenticatedUser) -> list[ExternalAccessGrantResponse]:
    try:
        grants = list_external_access_grants_for_owned_ledger(request.app.state.databases.open_registry, user.uuid, ledger_uuid)
    except LedgerNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ledger not found") from error
    return [
        ExternalAccessGrantResponse(
            grant_uuid=grant.uuid,
            external_access_uuid=access.uuid,
            name=access.name,
            created_at=grant.created_at,
        )
        for grant, access in grants
    ]


@router.post("", response_model=CreatedExternalAccessGrantResponse, status_code=status.HTTP_201_CREATED,)
async def create_ledger_external_access(
    ledger_uuid: UUID,
    payload: CreateExternalAccessRequest,
    response: Response,
    request: Request,
    user: AuthenticatedUser,
) -> CreatedExternalAccessGrantResponse:
    try:
        grant, token = await execute_credential_operation(
            request,
            partial(
                create_external_ledger_grant,
                request.app.state.databases.open_registry,
                request.app.state.password_hasher,
                user,
                ledger_uuid,
                payload.name,
                payload.current_password,
                int(time.time()),
                request.app.state.totp_authenticator,
                payload.totp_code,
            ),
        )
    except LedgerNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ledger not found") from error
    except TotpRequiredError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="TOTP required") from error
    except TotpCodeAlreadyUsedError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="TOTP code already used") from error
    except InvalidTotpCodeError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code") from error
    except InvalidCurrentPasswordError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid current password") from error
    response.headers["Cache-Control"] = "no-store"
    return CreatedExternalAccessGrantResponse(
        grant_uuid=grant.uuid,
        external_access_uuid=grant.grantee_uuid,
        name=payload.name,
        created_at=grant.created_at,
        token=token,
    )


@router.delete("/{grant_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_ledger_external_access(
    ledger_uuid: UUID,
    grant_uuid: UUID,
    payload: RevokeExternalAccessRequest,
    request: Request,
    user: AuthenticatedUser,
) -> None:
    try:
        await execute_credential_operation(
            request,
            partial(
                revoke_external_access_grant_from_owned_ledger,
                request.app.state.databases.open_registry,
                request.app.state.password_hasher,
                user,
                ledger_uuid,
                grant_uuid,
                payload.current_password,
                int(time.time()),
                request.app.state.totp_authenticator,
                payload.totp_code,
            ),
        )
    except LedgerGrantNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="External access not found") from error
    except TotpRequiredError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="TOTP required") from error
    except TotpCodeAlreadyUsedError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="TOTP code already used") from error
    except InvalidTotpCodeError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code") from error
    except InvalidCurrentPasswordError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid current password") from error
