import unittest

from pydantic import ValidationError

from app.domain.registry.model.totp import TotpStatus


class TotpStatusTest(unittest.TestCase):
    def test_pending_status_requires_complete_setup_details(self) -> None:
        for values in (
            {"state": "PENDING"},
            {"state": "PENDING", "provisioning_uri": "otpauth://totp/Moedeiro:Alice"},
            {"state": "PENDING", "expires_at": 100},
        ):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                TotpStatus(**values)

    def test_non_pending_status_rejects_setup_details(self) -> None:
        for state in ("ENABLED", "DISABLED"):
            with self.subTest(state=state), self.assertRaises(ValidationError):
                TotpStatus(state=state, provisioning_uri="otpauth://totp/Moedeiro:Alice", expires_at=100)

    def test_accepts_complete_pending_and_plain_non_pending_states(self) -> None:
        pending = TotpStatus(state="PENDING", provisioning_uri="otpauth://totp/Moedeiro:Alice", expires_at=100)

        self.assertEqual(pending.expires_at, 100)
        self.assertEqual(TotpStatus(state="ENABLED").state, "ENABLED")
        self.assertEqual(TotpStatus(state="DISABLED").state, "DISABLED")
