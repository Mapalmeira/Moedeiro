import unittest
from uuid import uuid4

from pydantic import TypeAdapter, ValidationError

from app.domain.registry.model.user_invitation import DEFAULT_EXPIRATION_TIMEOUT_SECONDS, InvitationCode, UserInvitation


class UserInvitationTest(unittest.TestCase):
    def create_invitation(self, **changes) -> UserInvitation:
        values = {"uuid": uuid4(), "secret_hash": b"s" * 32, "created_at": 10, "expires_at": 10 + DEFAULT_EXPIRATION_TIMEOUT_SECONDS}
        values.update(changes)
        return UserInvitation(**values)

    def test_accepts_an_active_invitation_with_one_hour_lifetime(self) -> None:
        invitation = self.create_invitation()

        self.assertEqual(invitation.expires_at, 10 + DEFAULT_EXPIRATION_TIMEOUT_SECONDS)
        self.assertIsNone(invitation.consumed_at)
        self.assertIsNone(invitation.revoked_at)

    def test_expiration_must_follow_creation(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_invitation(expires_at=10)

    def test_state_timestamps_cannot_precede_creation(self) -> None:
        for field in ("consumed_at", "revoked_at"):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError):
                    self.create_invitation(**{field: 9})

    def test_consumption_must_precede_expiration(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_invitation(expires_at=20, consumed_at=20)

    def test_cannot_be_consumed_and_revoked(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_invitation(consumed_at=11, revoked_at=12)

    def test_invitation_code_uses_the_crockford_alphabet_and_fixed_length(self) -> None:
        adapter = TypeAdapter(InvitationCode)

        self.assertEqual(adapter.validate_python("7KMQP3WX9RDTH6VN"), "7KMQP3WX9RDTH6VN")
        for value in ("short", "7KMQP3WX9RDTH6VI"):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    adapter.validate_python(value)


if __name__ == "__main__":
    unittest.main()
