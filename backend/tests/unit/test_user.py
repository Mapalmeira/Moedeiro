import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.registry.model.user import User, normalize_user_name


class UserTest(unittest.TestCase):
    def create_user(self, **changes) -> User:
        values = {"uuid": uuid4(), "name": "ÁLICE", "normalized_name": "álice", "password_hash": "$argon2id$encoded", "created_at": 10, "password_changed_at": 10}
        values.update(changes)
        return User(**values)

    def test_normalizes_whitespace_case_and_unicode_compatibility(self) -> None:
        self.assertEqual(normalize_user_name("  ＡLICE  "), "alice")

    def test_accepts_a_name_and_matching_normalized_name(self) -> None:
        user = self.create_user()

        self.assertEqual(user.normalized_name, "álice")

    def test_rejects_a_normalized_name_that_does_not_match(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_user(normalized_name="alice")

    def test_enforces_user_name_limits(self) -> None:
        invalid_values = ({"name": "", "normalized_name": ""}, {"name": "x" * 51, "normalized_name": "x" * 51})
        for changes in invalid_values:
            with self.subTest(changes=changes):
                with self.assertRaises(ValidationError):
                    self.create_user(**changes)

    def test_password_change_cannot_precede_creation(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_user(password_changed_at=9)


if __name__ == "__main__":
    unittest.main()
