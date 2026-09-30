import unittest

from app.infrastructure.persistence.sqlite.search import normalize_search


class SearchNormalizationTest(unittest.TestCase):
    def test_normalizes_case_and_diacritics(self) -> None:
        self.assertEqual(normalize_search("Café À LA CARTE"), "cafe a la carte")
        self.assertIsNone(normalize_search(None))
