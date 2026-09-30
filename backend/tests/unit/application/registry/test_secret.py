import hashlib
import unittest
from unittest.mock import patch

from app.application.registry.secret import generate_opaque_token, hash_ascii_secret, try_hash_ascii_secret


class SecretTest(unittest.TestCase):
    @patch("app.application.registry.secret.secrets.token_urlsafe", return_value="opaque-token")
    def test_generate_opaque_token_returns_token_and_hash(self, token_urlsafe) -> None:
        token, token_hash = generate_opaque_token()

        self.assertEqual(token, "opaque-token")
        self.assertEqual(token_hash, hashlib.sha256(b"opaque-token").digest())
        token_urlsafe.assert_called_once_with(32)

    def test_hash_ascii_secret_rejects_non_ascii_values(self) -> None:
        with self.assertRaises(UnicodeEncodeError):
            hash_ascii_secret("token-ç")

    def test_try_hash_ascii_secret_returns_none_for_non_ascii_values(self) -> None:
        self.assertIsNone(try_hash_ascii_secret("token-ç"))
