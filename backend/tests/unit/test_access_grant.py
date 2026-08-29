"""Unit tests for the access grant model."""

import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.registry.model.access_grant import AccessGrant


class AccessGrantTest(unittest.TestCase):
    def create_grant(self, **changes) -> AccessGrant:
        values = {"uuid": uuid4(), "ledger_uuid": uuid4(), "authentication_method": "WEBCRYPTO", "public_key": b"public-key", "algorithm": "ES256", "created_at": 10}
        values.update(changes)
        return AccessGrant(**values)

    def test_accepts_webcrypto_without_authenticator_state(self) -> None:
        grant = self.create_grant()

        self.assertEqual(grant.authentication_method, "WEBCRYPTO")
        self.assertIsNone(grant.credential_id)
        self.assertIsNone(grant.signature_counter)

    def test_accepts_webauthn_with_credential_and_counter(self) -> None:
        grant = self.create_grant(authentication_method="WEBAUTHN", credential_id=b"credential-id", signature_counter=0)

        self.assertEqual(grant.authentication_method, "WEBAUTHN")
        self.assertEqual(grant.signature_counter, 0)

    def test_webcrypto_rejects_webauthn_state(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_grant(credential_id=b"credential-id")

    def test_webauthn_requires_credential_and_counter(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_grant(authentication_method="WEBAUTHN", credential_id=b"credential-id")

    def test_enforces_label_and_binary_field_limits(self) -> None:
        invalid_values = ({"label": "x" * 31}, {"public_key": b""}, {"public_key": b"x" * 4097})
        for changes in invalid_values:
            with self.subTest(changes=changes):
                with self.assertRaises(ValidationError):
                    self.create_grant(**changes)

    def test_revocation_cannot_precede_creation(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_grant(revoked_at=9)


if __name__ == "__main__":
    unittest.main()
