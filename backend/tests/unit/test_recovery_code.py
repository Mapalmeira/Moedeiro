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
        code = self.create_code()

        self.assertIsNone(code.used_at)
        self.assertIsNone(code.revoked_at)

    def test_usage_cannot_precede_creation(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_code(used_at=9)

    def test_revocation_cannot_precede_creation(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_code(revoked_at=9)

    def test_code_cannot_be_used_and_revoked(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_code(used_at=11, revoked_at=12)


if __name__ == "__main__":
    unittest.main()
