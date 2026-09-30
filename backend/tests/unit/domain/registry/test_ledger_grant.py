import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.registry.model.ledger_grant import LedgerGrant


class LedgerGrantTest(unittest.TestCase):
    def create_grant(self, **changes) -> LedgerGrant:
        values = {
            "uuid": uuid4(),
            "grantee_uuid": uuid4(),
            "ledger_uuid": uuid4(),
            "role": "OWNER",
            "created_at": 10,
        }
        values.update(changes)
        return LedgerGrant(**values)

    def test_accepts_supported_roles(self) -> None:
        self.assertEqual(self.create_grant().role, "OWNER")
        self.assertEqual(self.create_grant(role="GUEST").role, "GUEST")

    def test_rejects_unsupported_roles(self) -> None:
        for role in ("EDITOR", "READER", "ADMIN"):
            with self.subTest(role=role):
                with self.assertRaises(ValidationError):
                    self.create_grant(role=role)

    def test_revocation_cannot_precede_creation(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_grant(revoked_at=9)
