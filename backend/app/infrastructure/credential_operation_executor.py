import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore
from typing import TypeVar


Result = TypeVar("Result")


class CredentialOperationCapacityExceededError(Exception):
    pass


class CredentialOperationExecutor:
    def __init__(self, concurrency: int):
        self._semaphore = BoundedSemaphore(concurrency)
        self._executor = ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="credential-operation")

    async def run(self, operation: Callable[[], Result]) -> Result:
        if not self._semaphore.acquire(blocking=False):
            raise CredentialOperationCapacityExceededError
        try:
            return await asyncio.wrap_future(self._executor.submit(operation))
        finally:
            self._semaphore.release()

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=True)
