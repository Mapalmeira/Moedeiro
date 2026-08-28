"""Unit tests for the registry ledger-token model."""

import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.registry.model.ledger_token import LedgerToken


class LedgerTokenTest(unittest.TestCase):
    def test_accepts_optional_label_and_revocation_timestamp(self) -> None:
        active_token = LedgerToken(
            uuid=uuid4(),
            ledger_uuid=uuid4(),
            token_hash="active-hash",
            created_at=10,
        )
        revoked_token = LedgerToken(
            uuid=uuid4(),
            ledger_uuid=uuid4(),
            token_hash="revoked-hash",
            label="phone",
            created_at=10,
            revoked_at=20,
        )

        self.assertIsNone(active_token.label)
        self.assertIsNone(active_token.revoked_at)
        self.assertEqual(revoked_token.label, "phone")
        self.assertEqual(revoked_token.revoked_at, 20)

    def test_accepts_token_hash_at_length_boundaries(self) -> None:
        for token_hash in ("x", "x" * 255):
            with self.subTest(token_hash_length=len(token_hash)):
                token = LedgerToken(
                    uuid=uuid4(),
                    ledger_uuid=uuid4(),
                    token_hash=token_hash,
                    created_at=10,
                )
                self.assertEqual(token.token_hash, token_hash)

    def test_rejects_token_hash_outside_length_limits(self) -> None:
        for token_hash in ("", "x" * 256):
            with self.subTest(token_hash_length=len(token_hash)):
                with self.assertRaises(ValidationError):
                    LedgerToken(
                        uuid=uuid4(),
                        ledger_uuid=uuid4(),
                        token_hash=token_hash,
                        created_at=10,
                    )

    def test_rejects_label_longer_than_limit(self) -> None:
        with self.assertRaises(ValidationError):
            LedgerToken(
                uuid=uuid4(),
                ledger_uuid=uuid4(),
                token_hash="token-hash",
                label="x" * 31,
                created_at=10,
            )


if __name__ == "__main__":
    unittest.main()
