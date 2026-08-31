import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.registry.model.remember_session import DEFAULT_EXPIRATION_TIMEOUT_SECONDS, RememberSession


class RememberSessionTest(unittest.TestCase):
    def create_session(self, **changes) -> RememberSession:
        values = {"uuid": uuid4(), "user_uuid": uuid4(), "token_hash": b"t" * 32, "created_at": 10}
        values.update(changes)
        return RememberSession(**values)

    def test_uses_a_30_day_expiration_by_default(self) -> None:
        session = self.create_session()

        self.assertEqual(session.expiration_timeout_seconds, 30 * 24 * 60 * 60)
        self.assertEqual(session.expiration_timeout_seconds, DEFAULT_EXPIRATION_TIMEOUT_SECONDS)
        self.assertIsNone(session.last_used_at)
        self.assertIsNone(session.revoked_at)

    def test_expiration_timeout_must_be_positive(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_session(expiration_timeout_seconds=0)

    def test_state_timestamps_cannot_precede_creation(self) -> None:
        for field in ("last_used_at", "revoked_at"):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError):
                    self.create_session(**{field: 9})

    def test_last_use_must_precede_expiration(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_session(expiration_timeout_seconds=10, last_used_at=20)


if __name__ == "__main__":
    unittest.main()
