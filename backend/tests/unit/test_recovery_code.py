import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.registry.model.recovery_code import RecoveryCode


class RecoveryCodeTest(unittest.TestCase):
    def create_code(self, **changes) -> RecoveryCode:
        values = {"uuid": uuid4(), "user_uuid": uuid4(), "code_hash": b"c" * 32, "created_at": 10}
        values.update(changes)
        return RecoveryCode(**values)

    def test_accepts_an_unused_code(self) -> None:
        self.assertIsNone(self.create_code().used_at)

    def test_does_not_validate_backend_managed_code_hash(self) -> None:
        self.assertEqual(self.create_code(code_hash=b"").code_hash, b"")

    def test_usage_cannot_precede_creation(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_code(used_at=9)


if __name__ == "__main__":
    unittest.main()
