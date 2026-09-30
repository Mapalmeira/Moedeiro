import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domain.registry.model.external_access import ExternalAccess


class ExternalAccessTest(unittest.TestCase):
    def create_access(self, **changes) -> ExternalAccess:
        values = {"uuid": uuid4(), "name": "Sync plugin", "token_hash": b"t" * 32}
        values.update(changes)
        return ExternalAccess(**values)

    def test_enforces_name_length(self) -> None:
        for name in ("", "x" * 51):
            with self.subTest(name_length=len(name)):
                with self.assertRaises(ValidationError):
                    self.create_access(name=name)

    def test_enforces_sha256_hash_length(self) -> None:
        for token_hash in (b"x" * 31, b"x" * 33):
            with self.subTest(hash_length=len(token_hash)):
                with self.assertRaises(ValidationError):
                    self.create_access(token_hash=token_hash)
