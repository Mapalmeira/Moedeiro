from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pydantic import ValidationError

from app.settings import Settings


class SettingsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.registry_schema_path = self.directory / "registry.sql"
        self.ledger_schema_path = self.directory / "ledger.sql"
        self.registry_schema_path.write_text("SELECT 1", encoding="utf-8")
        self.ledger_schema_path.write_text("SELECT 1", encoding="utf-8")
        self.environment = {
            "REGISTRY_SCHEMA_PATH": str(self.registry_schema_path),
            "LEDGER_SCHEMA_PATH": str(self.ledger_schema_path),
            "REGISTRY_DB_PATH": str(self.directory / "registry/registry.sqlite"),
            "LEDGER_DBS_DIR": str(self.directory / "ledgers"),
        }

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_reads_every_required_path_from_the_environment(self) -> None:
        settings = Settings.from_environment(self.environment)

        self.assertEqual(settings.registry_schema_path, self.registry_schema_path)
        self.assertEqual(settings.ledger_schema_path, self.ledger_schema_path)
        self.assertEqual(settings.registry_db_path, self.directory / "registry/registry.sqlite")
        self.assertEqual(settings.ledger_dbs_dir, self.directory / "ledgers")
        self.assertEqual(settings.registration_validate_ip_rate_limit, "5/hour")
        self.assertEqual(settings.registration_create_ip_rate_limit, "5/hour")
        self.assertEqual(settings.login_ip_rate_limit, "5/minute")
        self.assertEqual(settings.password_hash_concurrency, 2)

    def test_reads_security_limits_from_the_environment(self) -> None:
        environment = {
            **self.environment,
            "REGISTRATION_VALIDATE_IP_RATE_LIMIT": "3/minute",
            "REGISTRATION_CREATE_IP_RATE_LIMIT": "2/hour",
            "LOGIN_IP_RATE_LIMIT": "4/minute",
            "PASSWORD_HASH_CONCURRENCY": "1",
        }

        settings = Settings.from_environment(environment)

        self.assertEqual(settings.registration_validate_ip_rate_limit, "3/minute")
        self.assertEqual(settings.registration_create_ip_rate_limit, "2/hour")
        self.assertEqual(settings.login_ip_rate_limit, "4/minute")
        self.assertEqual(settings.password_hash_concurrency, 1)

    def test_rejects_invalid_security_limits(self) -> None:
        invalid_values = (
            ("REGISTRATION_VALIDATE_IP_RATE_LIMIT", "invalid"),
            ("REGISTRATION_VALIDATE_IP_RATE_LIMIT", "0/minute"),
            ("REGISTRATION_CREATE_IP_RATE_LIMIT", ""),
            ("LOGIN_IP_RATE_LIMIT", "0/minute"),
            ("PASSWORD_HASH_CONCURRENCY", "0"),
        )

        for variable, value in invalid_values:
            with self.subTest(variable=variable, value=value):
                with self.assertRaises((ValueError, ValidationError)):
                    Settings.from_environment({**self.environment, variable: value})

    def test_rejects_a_missing_or_empty_environment_variable(self) -> None:
        for value in (None, ""):
            with self.subTest(value=value):
                environment = dict(self.environment)
                if value is None:
                    del environment["REGISTRY_DB_PATH"]
                else:
                    environment["REGISTRY_DB_PATH"] = value
                with self.assertRaisesRegex(ValueError, "REGISTRY_DB_PATH must be defined"):
                    Settings.from_environment(environment)

    def test_rejects_missing_schema_files(self) -> None:
        environment = dict(self.environment)
        environment["LEDGER_SCHEMA_PATH"] = str(self.directory / "missing.sql")

        with self.assertRaises(ValidationError):
            Settings.from_environment(environment)

    def test_rejects_data_paths_with_the_wrong_existing_type(self) -> None:
        registry_directory = self.directory / "registry-path"
        registry_directory.mkdir()
        ledger_file = self.directory / "ledger-path"
        ledger_file.touch()
        invalid_values = (
            ("registry_db_path", registry_directory),
            ("ledger_dbs_dir", ledger_file),
        )

        for field, value in invalid_values:
            with self.subTest(field=field):
                values = {
                    "registry_schema_path": self.registry_schema_path,
                    "ledger_schema_path": self.ledger_schema_path,
                    "registry_db_path": self.directory / "registry.sqlite",
                    "ledger_dbs_dir": self.directory / "ledgers",
                }
                values[field] = value
                with self.assertRaises(ValidationError):
                    Settings.model_validate(values)


if __name__ == "__main__":
    unittest.main()
