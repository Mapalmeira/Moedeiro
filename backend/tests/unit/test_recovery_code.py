import unittest
from uuid import uuid4

from pydantic import TypeAdapter, ValidationError

from app.domain.registry.model.recovery_code import RecoveryCode, RecoveryCodeValue


class RecoveryCodeTest(unittest.TestCase):
    def create_code(self, **changes) -> RecoveryCode:
        values = {"uuid": uuid4(), "user_uuid": uuid4(), "code_hash": b"c" * 32, "created_at": 10, "expires_at": 20}
        values.update(changes)
        return RecoveryCode(**values)

    def test_accepts_an_unused_code(self) -> None:
        code = self.create_code()

        self.assertIsNone(code.used_at)

    def test_usage_cannot_precede_creation(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_code(used_at=9)

    def test_expiration_must_follow_creation(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_code(expires_at=10)

    def test_usage_cannot_reach_expiration(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_code(used_at=20)

    def test_value_uses_16_crockford_characters(self) -> None:
        adapter = TypeAdapter(RecoveryCodeValue)
        value = "7KMQP3WX9RDTH6VN"

        self.assertEqual(adapter.validate_python(value), value)
        for invalid in (value[:-1], value + "0", value[:-1] + "I"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValidationError):
                    adapter.validate_python(invalid)


if __name__ == "__main__":
    unittest.main()
