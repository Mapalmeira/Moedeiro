import unittest

from app.domain.ledger.limits import MAXIMUM_ACCOUNTS, MAXIMUM_BUDGETS, MAXIMUM_CURRENCIES, MAXIMUM_FINANCIAL_EVENTS
from app.domain.registry.limits import MAXIMUM_EXTERNAL_ACCESSES_PER_LEDGER, MAXIMUM_LEDGERS_PER_USER


class DomainLimitsTest(unittest.TestCase):
    def test_collection_limits(self) -> None:
        self.assertEqual(MAXIMUM_LEDGERS_PER_USER, 10)
        self.assertEqual(MAXIMUM_EXTERNAL_ACCESSES_PER_LEDGER, 20)
        self.assertEqual(MAXIMUM_ACCOUNTS, 300)
        self.assertEqual(MAXIMUM_CURRENCIES, 300)
        self.assertEqual(MAXIMUM_BUDGETS, 1_000)
        self.assertEqual(MAXIMUM_FINANCIAL_EVENTS, 1_000_000)
