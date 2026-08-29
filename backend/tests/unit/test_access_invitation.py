"""Unit tests for the access invitation model."""

import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.registry.model.access_invitation import AccessInvitation


class AccessInvitationTest(unittest.TestCase):
    def create_invitation(self, **changes) -> AccessInvitation:
        values = {"uuid": uuid4(), "ledger_uuid": uuid4(), "grant_uuid": uuid4(), "secret_hash": b"s" * 32, "created_at": 10, "expires_at": 20}
        values.update(changes)
        return AccessInvitation(**values)

    def test_accepts_an_active_invitation(self) -> None:
        invitation = self.create_invitation()

        self.assertIsNone(invitation.consumed_at)
        self.assertIsNone(invitation.revoked_at)

    def test_requires_an_exactly_32_byte_secret_hash(self) -> None:
        for secret_hash in (b"s" * 31, b"s" * 33):
            with self.subTest(size=len(secret_hash)):
                with self.assertRaises(ValidationError):
                    self.create_invitation(secret_hash=secret_hash)

    def test_expiration_must_follow_creation(self) -> None:
        for expires_at in (9, 10):
            with self.subTest(expires_at=expires_at):
                with self.assertRaises(ValidationError):
                    self.create_invitation(expires_at=expires_at)

    def test_state_timestamps_cannot_precede_creation(self) -> None:
        for field in ("consumed_at", "revoked_at"):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError):
                    self.create_invitation(**{field: 9})

    def test_consumption_must_precede_expiration(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_invitation(consumed_at=20)

    def test_cannot_be_consumed_and_revoked(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_invitation(consumed_at=11, revoked_at=12)


if __name__ == "__main__":
    unittest.main()
