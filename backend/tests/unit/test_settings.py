from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pydantic import ValidationError

from app.settings import Settings


class SettingsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.environment = {
            "REGISTRY_DB_PATH": str(self.directory / "registry/registry.sqlite"),
            "LEDGER_DBS_DIR": str(self.directory / "ledgers"),
        }

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_reads_path_overrides_from_the_environment(self) -> None:
        frontend_dist_path = self.directory / "frontend"
        environment = {**self.environment, "FRONTEND_DIST_PATH": str(frontend_dist_path)}

        settings = Settings.from_environment(environment)

        project_root = Path(__file__).resolve().parents[3]
        self.assertEqual(
            settings.registry_schema_path,
            project_root / "backend/app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql",
        )
        self.assertEqual(
            settings.ledger_schema_path,
            project_root / "backend/app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql",
        )
        self.assertEqual(settings.registry_db_path, self.directory / "registry/registry.sqlite")
        self.assertEqual(settings.ledger_dbs_dir, self.directory / "ledgers")
        self.assertEqual(settings.frontend_dist_path, frontend_dist_path)
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
        self.assertEqual(settings.max_query_points, 500)
        self.assertIsNone(settings.trusted_proxy_ip)
        self.assertFalse(settings.allow_insecure_http)

    def test_uses_built_in_paths_when_environment_overrides_are_absent(self) -> None:
        settings = Settings.from_environment({})
        project_root = Path(__file__).resolve().parents[3]

        self.assertEqual(
            settings.registry_schema_path,
            project_root / "backend/app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql",
        )
        self.assertEqual(
            settings.ledger_schema_path,
            project_root / "backend/app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql",
        )
        self.assertEqual(settings.registry_db_path, project_root / "data/registry/registry.sqlite")
        self.assertEqual(settings.ledger_dbs_dir, project_root / "data/ledgers")
        self.assertEqual(settings.frontend_dist_path, project_root / "frontend/dist/moedeiro/browser")
        self.assertIsNone(settings.totp_encryption_key)

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
            "MAX_QUERY_POINTS": "750",
            "TRUSTED_PROXY_IP": "192.0.2.10",
            "ALLOW_INSECURE_HTTP": "true",
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
        self.assertEqual(settings.max_query_points, 750)
        self.assertEqual(str(settings.trusted_proxy_ip), "192.0.2.10")
        self.assertTrue(settings.allow_insecure_http)

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
            ("MAX_QUERY_POINTS", "0"),
            ("TRUSTED_PROXY_IP", "not-an-ip"),
            ("ALLOW_INSECURE_HTTP", "not-a-bool"),
        )

        for variable, value in invalid_values:
            with self.subTest(variable=variable, value=value):
                with self.assertRaises((ValueError, ValidationError)):
                    Settings.from_environment({**self.environment, variable: value})

    def test_rejects_empty_path_environment_overrides(self) -> None:
        for variable in (
            "REGISTRY_DB_PATH",
            "LEDGER_DBS_DIR",
            "FRONTEND_DIST_PATH",
        ):
            with self.subTest(variable=variable):
                with self.assertRaisesRegex(ValueError, f"{variable} must not be empty"):
                    Settings.from_environment({**self.environment, variable: "   "})

    def test_schema_paths_are_internal_and_not_environment_overrides(self) -> None:
        settings = Settings.from_environment(
            {
                **self.environment,
                "REGISTRY_SCHEMA_PATH": str(self.directory / "other-registry.sql"),
                "LEDGER_SCHEMA_PATH": str(self.directory / "other-ledger.sql"),
            }
        )
        project_root = Path(__file__).resolve().parents[3]

        self.assertEqual(
            settings.registry_schema_path,
            project_root / "backend/app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql",
        )
        self.assertEqual(
            settings.ledger_schema_path,
            project_root / "backend/app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql",
        )

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
                    "registry_db_path": self.directory / "registry.sqlite",
                    "ledger_dbs_dir": self.directory / "ledgers",
                }
                values[field] = value
                with self.assertRaises(ValidationError):
                    Settings.model_validate(values)

    def test_treats_empty_trusted_proxy_ip_as_unset(self) -> None:
        for value in ("", "   "):
            with self.subTest(value=value):
                settings = Settings.from_environment(
                    {**self.environment, "TRUSTED_PROXY_IP": value}
                )

                self.assertIsNone(settings.trusted_proxy_ip)

if __name__ == "__main__":
    unittest.main()
