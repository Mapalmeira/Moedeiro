import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.registry.model.mfa_method import MfaMethod


class MfaMethodTest(unittest.TestCase):
    def create_method(self, **changes) -> MfaMethod:
        values = {"uuid": uuid4(), "user_uuid": uuid4(), "type": "TOTP", "secret_encrypted": b"ciphertext", "created_at": 10, "expires_unconfirmed_at": 610}
        values.update(changes)
        return MfaMethod(**values)

    def test_accepts_totp(self) -> None:
        self.assertEqual(self.create_method().type, "TOTP")

    def test_rejects_confirmation_before_creation(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_method(confirmed_at=9)

    def test_rejects_a_pending_expiration_at_creation(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_method(expires_unconfirmed_at=10)

    def test_rejects_an_unsupported_type(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_method(type="SMS")
