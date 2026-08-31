import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.registry.model.ledger_grant import LedgerGrant


class LedgerGrantTest(unittest.TestCase):
    def create_grant(self, **changes) -> LedgerGrant:
        values = {"uuid": uuid4(), "user_uuid": uuid4(), "ledger_uuid": uuid4(), "role": "OWNER", "created_at": 10}
        values.update(changes)
        return LedgerGrant(**values)

    def test_accepts_every_supported_role(self) -> None:
        for role in ("OWNER", "EDITOR", "READER"):
            with self.subTest(role=role):
                self.assertEqual(self.create_grant(role=role).role, role)

    def test_rejects_an_unknown_role(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_grant(role="ADMIN")

    def test_revocation_cannot_precede_creation(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_grant(revoked_at=9)


if __name__ == "__main__":
    unittest.main()
