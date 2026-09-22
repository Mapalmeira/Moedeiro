import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.registry.model.ledger_grant import LedgerGrant


class LedgerGrantTest(unittest.TestCase):
    def create_grant(self, **changes) -> LedgerGrant:
        values = {"uuid": uuid4(), "user_uuid": uuid4(), "ledger_uuid": uuid4(), "type": "OWNER", "created_at": 10}
        values.update(changes)
        return LedgerGrant(**values)

    def test_accepts_supported_types(self) -> None:
        self.assertEqual(self.create_grant().type, "OWNER")
        self.assertEqual(self.create_grant(type="EXTERNAL_ACCESS").type, "EXTERNAL_ACCESS")

    def test_rejects_unsupported_types(self) -> None:
        for type in ("EDITOR", "READER", "ADMIN"):
            with self.subTest(type=type):
                with self.assertRaises(ValidationError):
                    self.create_grant(type=type)

    def test_revocation_cannot_precede_creation(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_grant(revoked_at=9)
