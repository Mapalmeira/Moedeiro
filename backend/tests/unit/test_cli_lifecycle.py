from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.cli import main
from app.settings import Settings


class CliLifecycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.settings = Settings(
            registry_db_path=self.directory / "registry/registry.sqlite",
            ledger_dbs_dir=self.directory / "ledgers",
            frontend_dist_path=self.directory / "frontend",
            totp_encryption_key="test-key",
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @patch("app.cli.start_server", return_value=0)
    def test_start_dispatches_to_the_service_launcher(self, start_server) -> None:
        result = main(
            ["start", "--host", "0.0.0.0", "--port", "9000"],
            self.settings,
        )

        self.assertEqual(result, 0)
        start_server.assert_called_once_with(
            self.settings,
            "0.0.0.0",
            9000,
            mount_frontend=True,
        )

    @patch("app.cli.start_server", return_value=0)
    def test_start_uses_native_address_defaults(self, start_server) -> None:
        result = main(["start"], self.settings)

        self.assertEqual(result, 0)
        start_server.assert_called_once_with(
            self.settings,
            "127.0.0.1",
            8000,
            mount_frontend=True,
        )

    @patch("app.cli.start_server", return_value=0)
    def test_start_can_serve_only_the_api(self, start_server) -> None:
        result = main(["start", "--api-only"], self.settings)

        self.assertEqual(result, 0)
        start_server.assert_called_once_with(
            self.settings,
            "127.0.0.1",
            8000,
            mount_frontend=False,
        )


if __name__ == "__main__":
    unittest.main()
