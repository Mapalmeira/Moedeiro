import unittest

from cryptography.fernet import Fernet

from app.infrastructure.security.totp_authenticator import FernetTotpAuthenticator


class FernetTotpAuthenticatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.authenticator = FernetTotpAuthenticator(Fernet.generate_key().decode("ascii"))

    def test_encrypts_the_secret_and_verifies_rfc6238_totp_codes(self) -> None:
        secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"

        encrypted_secret = self.authenticator.encrypt_secret(secret)

        self.assertNotEqual(encrypted_secret, secret.encode("ascii"))
        self.assertEqual(self.authenticator.decrypt_secret(encrypted_secret), secret)
        self.assertEqual(self.authenticator.verify(secret, "287082", 59), 1)
        self.assertIsNone(self.authenticator.verify(secret, "000000", 59))

    def test_creates_a_base32_secret_and_provisioning_uri(self) -> None:
        secret = self.authenticator.create_secret()

        self.assertEqual(len(secret), 32)
        self.assertTrue(secret.isupper())
        self.assertIn(f"secret={secret}", self.authenticator.provisioning_uri(secret, "Alice"))


if __name__ == "__main__":
    unittest.main()
