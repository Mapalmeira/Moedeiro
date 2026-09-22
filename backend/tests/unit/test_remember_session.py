import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.registry.model.remember_session import DEFAULT_EXPIRATION_TIMEOUT_SECONDS, RememberSession


class RememberSessionTest(unittest.TestCase):
    def create_session(self, **changes) -> RememberSession:
        values = {"uuid": uuid4(), "user_uuid": uuid4(), "token_hash": b"t" * 32, "created_at": 10, "expires_at": 10 + DEFAULT_EXPIRATION_TIMEOUT_SECONDS}
        values.update(changes)
        return RememberSession(**values)

    def test_accepts_an_active_session_with_30_day_expiration(self) -> None:
        session = self.create_session()

        self.assertEqual(session.expires_at, 10 + 30 * 24 * 60 * 60)
        self.assertIsNone(session.last_used_at)

    def test_expiration_must_follow_creation(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_session(expires_at=10)

    def test_last_use_cannot_precede_creation(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_session(last_used_at=9)

    def test_last_use_must_precede_expiration(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_session(expires_at=20, last_used_at=20)
