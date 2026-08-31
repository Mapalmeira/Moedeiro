"""Unit tests for the authentication session model."""

import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.registry.model.auth_session import AuthSession, DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, DEFAULT_INACTIVITY_TIMEOUT_SECONDS


class AuthSessionTest(unittest.TestCase):
    def create_session(self, **changes) -> AuthSession:
        values = {"uuid": uuid4(), "user_uuid": uuid4(), "token_hash": b"t" * 32, "created_at": 10, "expires_at": 10 + DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, "inactivity_timeout_seconds": DEFAULT_INACTIVITY_TIMEOUT_SECONDS}
        values.update(changes)
        return AuthSession(**values)

    def test_accepts_an_active_session(self) -> None:
        session = self.create_session()

        self.assertEqual(session.expires_at, 10 + 12 * 60 * 60)
        self.assertEqual(session.inactivity_timeout_seconds, 30 * 60)
        self.assertIsNone(session.last_activity_at)
        self.assertIsNone(session.revoked_at)

    def test_defines_timeouts_in_code(self) -> None:
        self.assertEqual(DEFAULT_INACTIVITY_TIMEOUT_SECONDS, 30 * 60)
        self.assertEqual(DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, 12 * 60 * 60)

    def test_activity_and_revocation_cannot_precede_creation(self) -> None:
        for field in ("last_activity_at", "revoked_at"):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError):
                    self.create_session(**{field: 9})

    def test_expiration_and_inactivity_timeout_must_be_valid(self) -> None:
        for changes in ({"expires_at": 10}, {"inactivity_timeout_seconds": 0}, {"last_activity_at": 10 + DEFAULT_ABSOLUTE_TIMEOUT_SECONDS}):
            with self.subTest(changes=changes):
                with self.assertRaises(ValidationError):
                    self.create_session(**changes)

if __name__ == "__main__":
    unittest.main()
