from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from app.application.ledger.exceptions import LedgerNotFoundError
from app.application.ledger.use_cases.ledger import access_granted_ledger, create_ledger, get_owned_ledger
from app.application.registry.exceptions import UserNotFoundError


class LedgerUseCasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.uuid = uuid4()
        self.unit_of_work = MagicMock()
        self.factory = MagicMock()
        self.factory.return_value.__enter__.return_value = self.unit_of_work

    def test_creation_rejects_a_user_deleted_concurrently(self) -> None:
        self.unit_of_work.user_repository.get.return_value = None

        with self.assertRaises(UserNotFoundError):
            create_ledger(self.factory, MagicMock(), MagicMock(), self.uuid, "Ledger", "lucide:BookOpen", b"\x80\x80\x80", 10)

    def test_access_rejects_a_ledger_deleted_after_its_grant_is_resolved(self) -> None:
        self.unit_of_work.ledger_grant_repository.get_active_by_grantee_and_ledger.return_value = SimpleNamespace(role="OWNER")
        self.unit_of_work.ledger_repository.get.return_value = None

        with self.assertRaises(LedgerNotFoundError):
            access_granted_ledger(self.factory, self.uuid, self.uuid, 10)

    def test_owner_lookup_rejects_a_ledger_deleted_after_its_grant_is_resolved(self) -> None:
        self.unit_of_work.ledger_grant_repository.get_active_owner_by_ledger.return_value = SimpleNamespace(grantee_uuid=self.uuid)
        self.unit_of_work.ledger_repository.get.return_value = None

        with self.assertRaises(LedgerNotFoundError):
            get_owned_ledger(self.factory, self.uuid, self.uuid)
