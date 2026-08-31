import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.registry.model.webauthn_credential import WebAuthnCredential


class WebAuthnCredentialTest(unittest.TestCase):
    def create_credential(self, **changes) -> WebAuthnCredential:
        values = {"uuid": uuid4(), "user_uuid": uuid4(), "credential_id": b"credential-id", "public_key": b"public-key", "sign_count": 0, "created_at": 10, "name": "Phone"}
        values.update(changes)
        return WebAuthnCredential(**values)

    def test_accepts_an_unused_credential(self) -> None:
        credential = self.create_credential()

        self.assertEqual(credential.sign_count, 0)
        self.assertIsNone(credential.last_used_at)

    def test_enforces_user_defined_name_limits(self) -> None:
        for name in ("", "x" * 51):
            with self.subTest(name=name):
                with self.assertRaises(ValidationError):
                    self.create_credential(name=name)

    def test_does_not_validate_backend_managed_binary_fields(self) -> None:
        for field, value in (("credential_id", b""), ("credential_id", b"x" * 10000), ("public_key", b""), ("public_key", b"x" * 10000)):
            with self.subTest(field=field, size=len(value)):
                self.assertEqual(getattr(self.create_credential(**{field: value}), field), value)

    def test_sign_count_cannot_be_negative(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_credential(sign_count=-1)

    def test_last_use_cannot_precede_creation(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_credential(last_used_at=9)


if __name__ == "__main__":
    unittest.main()
