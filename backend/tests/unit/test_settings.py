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
        self.assertEqual(settings.registration_ip_attempts_rate_limit, "5/hour")
        self.assertEqual(settings.login_ip_attempts_rate_limit, "5/minute")
        self.assertEqual(settings.password_recovery_ip_attempts_rate_limit, "5/hour")
        self.assertEqual(settings.totp_setup_ip_attempts_rate_limit, "5/hour")
        self.assertEqual(settings.refresh_ip_attempts_rate_limit, "10/minute")
        self.assertEqual(settings.authenticated_user_operations_rate_limit, "50/minute")
        self.assertEqual(settings.sync_route_concurrency, 40)
        self.assertEqual(settings.credential_operation_concurrency, 8)
        self.assertEqual(settings.password_hash_concurrency, 2)
        self.assertEqual(settings.max_page_size, 200)
        self.assertEqual(settings.max_category_tree_size, 1000)
        self.assertEqual(settings.max_shopping_list_movements, 300)
        self.assertEqual(settings.max_query_points, 500)

    def test_reads_security_limits_from_the_environment(self) -> None:
        environment = {
            **self.environment,
            "REGISTRATION_IP_ATTEMPTS_RATE_LIMIT": "2/hour",
            "LOGIN_IP_ATTEMPTS_RATE_LIMIT": "4/minute",
            "PASSWORD_RECOVERY_IP_ATTEMPTS_RATE_LIMIT": "2/hour",
            "TOTP_SETUP_IP_ATTEMPTS_RATE_LIMIT": "3/hour",
            "REFRESH_IP_ATTEMPTS_RATE_LIMIT": "4/minute",
            "AUTHENTICATED_USER_OPERATIONS_RATE_LIMIT": "90/minute",
            "SYNC_ROUTE_CONCURRENCY": "24",
            "CREDENTIAL_OPERATION_CONCURRENCY": "6",
            "PASSWORD_HASH_CONCURRENCY": "1",
            "MAX_PAGE_SIZE": "150",
            "MAX_CATEGORY_TREE_SIZE": "500",
            "MAX_SHOPPING_LIST_MOVEMENTS": "250",
            "MAX_QUERY_POINTS": "750",
        }

        settings = Settings.from_environment(environment)

        self.assertEqual(settings.registration_ip_attempts_rate_limit, "2/hour")
        self.assertEqual(settings.login_ip_attempts_rate_limit, "4/minute")
        self.assertEqual(settings.password_recovery_ip_attempts_rate_limit, "2/hour")
        self.assertEqual(settings.totp_setup_ip_attempts_rate_limit, "3/hour")
        self.assertEqual(settings.refresh_ip_attempts_rate_limit, "4/minute")
        self.assertEqual(settings.authenticated_user_operations_rate_limit, "90/minute")
        self.assertEqual(settings.sync_route_concurrency, 24)
        self.assertEqual(settings.credential_operation_concurrency, 6)
        self.assertEqual(settings.password_hash_concurrency, 1)
        self.assertEqual(settings.max_page_size, 150)
        self.assertEqual(settings.max_category_tree_size, 500)
        self.assertEqual(settings.max_shopping_list_movements, 250)
        self.assertEqual(settings.max_query_points, 750)

    def test_rejects_invalid_security_limits(self) -> None:
        invalid_values = (
            ("REGISTRATION_IP_ATTEMPTS_RATE_LIMIT", ""),
            ("LOGIN_IP_ATTEMPTS_RATE_LIMIT", "0/minute"),
            ("PASSWORD_RECOVERY_IP_ATTEMPTS_RATE_LIMIT", "invalid"),
            ("TOTP_SETUP_IP_ATTEMPTS_RATE_LIMIT", "0/minute"),
            ("REFRESH_IP_ATTEMPTS_RATE_LIMIT", "0/minute"),
            ("AUTHENTICATED_USER_OPERATIONS_RATE_LIMIT", "0/minute"),
            ("SYNC_ROUTE_CONCURRENCY", "0"),
            ("CREDENTIAL_OPERATION_CONCURRENCY", "0"),
            ("PASSWORD_HASH_CONCURRENCY", "0"),
            ("MAX_PAGE_SIZE", "0"),
            ("MAX_CATEGORY_TREE_SIZE", "0"),
            ("MAX_SHOPPING_LIST_MOVEMENTS", "0"),
            ("MAX_QUERY_POINTS", "0"),
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
