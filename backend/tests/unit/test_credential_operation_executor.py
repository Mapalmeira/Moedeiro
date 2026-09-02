import asyncio
from concurrent.futures import Future
import unittest
from unittest.mock import patch

from app.infrastructure.credential_operation_executor import CredentialOperationCapacityExceededError, CredentialOperationExecutor


class CredentialOperationExecutorTest(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_excess_work_instead_of_queueing_it(self) -> None:
        executor = CredentialOperationExecutor(1)
        pending = Future()

        with patch.object(executor._executor, "submit", return_value=pending):
            running = asyncio.create_task(executor.run(lambda: "running"))
            await asyncio.sleep(0)

            with self.assertRaises(CredentialOperationCapacityExceededError):
                await executor.run(lambda: "queued")

            running.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await running

        executor.shutdown()


if __name__ == "__main__":
    unittest.main()
