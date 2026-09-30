import unittest
from unittest.mock import MagicMock

from app.application.registry.exceptions import UserNameUnavailableError
from app.application.registry.use_cases.user import create_user


class UserUseCasesTest(unittest.TestCase):
    def test_creation_rejects_a_name_claimed_concurrently(self) -> None:
        unit_of_work = MagicMock()
        unit_of_work.user_repository.get_by_normalized_name.return_value = object()
        factory = MagicMock()
        factory.return_value.__enter__.return_value = unit_of_work

        with self.assertRaises(UserNameUnavailableError):
            create_user(factory, MagicMock(hash=MagicMock(return_value="hash")), "Alice", "valid password", 10)
