"""Unit tests for the authentication session model."""

import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.registry.model.auth_session import AuthSession, DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, DEFAULT_INACTIVITY_TIMEOUT_SECONDS


class AuthSessionTest(unittest.TestCase):
    def create_session(self, **changes) -> AuthSession:
        values = {"uuid": uuid4(), "grant_uuid": uuid4(), "token_hash": b"t" * 32, "created_at": 10}
        values.update(changes)
        return AuthSession(**values)

    def test_accepts_an_active_session(self) -> None:
        session = self.create_session()

        self.assertEqual(session.inactivity_timeout_seconds, 30 * 60)
        self.assertEqual(session.inactivity_timeout_seconds, DEFAULT_INACTIVITY_TIMEOUT_SECONDS)
        self.assertEqual(session.absolute_timeout_seconds, 12 * 60 * 60)
        self.assertEqual(session.absolute_timeout_seconds, DEFAULT_ABSOLUTE_TIMEOUT_SECONDS)
        self.assertIsNone(session.last_activity_at)
        self.assertIsNone(session.revoked_at)

    def test_requires_an_exactly_32_byte_token_hash(self) -> None:
        for token_hash in (b"t" * 31, b"t" * 33):
            with self.subTest(size=len(token_hash)):
                with self.assertRaises(ValidationError):
                    self.create_session(token_hash=token_hash)

    def test_timeouts_must_be_positive(self) -> None:
        for field in ("inactivity_timeout_seconds", "absolute_timeout_seconds"):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError):
                    self.create_session(**{field: 0})

    def test_inactivity_timeout_cannot_exceed_absolute_timeout(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_session(inactivity_timeout_seconds=101, absolute_timeout_seconds=100)

    def test_activity_and_revocation_cannot_precede_creation(self) -> None:
        for field in ("last_activity_at", "revoked_at"):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError):
                    self.create_session(**{field: 9})

    def test_activity_must_precede_absolute_timeout(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_session(absolute_timeout_seconds=100, last_activity_at=110)


if __name__ == "__main__":
    unittest.main()
