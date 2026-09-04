from collections.abc import Callable
from typing import TypeVar

from fastapi import HTTPException, Request, status

from app.infrastructure.concurrency.concurrent_password_hasher import PasswordHashCapacityExceededError
from app.infrastructure.concurrency.credential_operation_executor import CredentialOperationCapacityExceededError, CredentialOperationExecutor


Result = TypeVar("Result")


async def execute_credential_operation(request: Request, operation: Callable[[], Result]) -> Result:
    try:
        return await _executor(request).run(operation)
    except CredentialOperationCapacityExceededError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Credential operation capacity exhausted", headers={"Retry-After": "1"}) from error
    except PasswordHashCapacityExceededError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Password hashing capacity exhausted", headers={"Retry-After": "1"}) from error


def _executor(request: Request) -> CredentialOperationExecutor:
    return request.app.state.credential_operation_executor
