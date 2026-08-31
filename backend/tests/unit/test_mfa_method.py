import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.registry.model.mfa_method import MfaMethod


class MfaMethodTest(unittest.TestCase):
    def create_method(self, **changes) -> MfaMethod:
        values = {"uuid": uuid4(), "user_uuid": uuid4(), "type": "TOTP", "secret_encrypted": b"ciphertext", "created_at": 10}
        values.update(changes)
        return MfaMethod(**values)

    def test_accepts_totp(self) -> None:
        self.assertEqual(self.create_method().type, "TOTP")

    def test_rejects_an_unsupported_type(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_method(type="SMS")

if __name__ == "__main__":
    unittest.main()
