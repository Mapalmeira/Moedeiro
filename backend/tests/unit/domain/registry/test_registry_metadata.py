import unittest

from pydantic import ValidationError

from app.domain.registry.model.registry_metadata import RegistryMetadata


class RegistryMetadataTest(unittest.TestCase):
    def test_accepts_a_positive_schema_version(self) -> None:
        self.assertEqual(RegistryMetadata(schema_version=1).schema_version, 1)

    def test_rejects_a_nonpositive_schema_version(self) -> None:
        for schema_version in (0, -1):
            with self.subTest(schema_version=schema_version):
                with self.assertRaises(ValidationError):
                    RegistryMetadata(schema_version=schema_version)
