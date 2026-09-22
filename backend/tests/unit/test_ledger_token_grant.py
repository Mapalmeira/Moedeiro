import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.registry.model.ledger_grant import LedgerGrant
from app.domain.registry.model.ledger_token_grant import LedgerTokenGrant


class LedgerTokenGrantTest(unittest.TestCase):
    def create_grant(self, type="EXTERNAL_ACCESS") -> LedgerGrant:
        return LedgerGrant(
            uuid=uuid4(),
            user_uuid=uuid4(),
            ledger_uuid=uuid4(),
            type=type,
            created_at=10,
        )

    def create_token_grant(self, **changes) -> LedgerTokenGrant:
        values = {"grant": self.create_grant(), "name": "Sync plugin", "token_hash": b"t" * 32}
        values.update(changes)
        return LedgerTokenGrant(**values)

    def test_accepts_external_access_grant(self) -> None:
        token_grant = self.create_token_grant()

        self.assertEqual(token_grant.grant.type, "EXTERNAL_ACCESS")

    def test_rejects_owner_grant(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_token_grant(grant=self.create_grant(type="OWNER"))

    def test_enforces_name_length(self) -> None:
        for name in ("", "x" * 51):
            with self.subTest(name_length=len(name)):
                with self.assertRaises(ValidationError):
                    self.create_token_grant(name=name)

    def test_enforces_sha256_hash_length(self) -> None:
        for token_hash in (b"x" * 31, b"x" * 33):
            with self.subTest(hash_length=len(token_hash)):
                with self.assertRaises(ValidationError):
                    self.create_token_grant(token_hash=token_hash)


if __name__ == "__main__":
    unittest.main()
