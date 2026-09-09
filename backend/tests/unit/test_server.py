from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.server import start
from app.settings import Settings


class ServerLifecycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def settings(self, *, totp_encryption_key: str | None = "test-key") -> Settings:
        return Settings(
            registry_db_path=self.directory / "registry/registry.sqlite",
            ledger_dbs_dir=self.directory / "ledgers",
            frontend_dist_path=self.directory / "frontend",
            totp_encryption_key=totp_encryption_key,
        )

    @patch("app.server.uvicorn.run")
    @patch("app.server.create_app")
    def test_start_runs_in_the_foreground_on_the_selected_address(self, create_app, uvicorn_run) -> None:
        settings = self.settings()
        application = create_app.return_value

        result = start(settings, "0.0.0.0", 9000)

        self.assertEqual(result, 0)
        create_app.assert_called_once_with(settings=settings, mount_frontend=True)
        uvicorn_run.assert_called_once_with(application, host="0.0.0.0", port=9000)

    @patch("app.server.uvicorn.run")
    @patch("app.server.create_app")
    def test_start_can_run_without_mounting_the_frontend(self, create_app, uvicorn_run) -> None:
        settings = self.settings()
        application = create_app.return_value

        result = start(settings, mount_frontend=False)

        self.assertEqual(result, 0)
        create_app.assert_called_once_with(settings=settings, mount_frontend=False)
        uvicorn_run.assert_called_once_with(application, host="127.0.0.1", port=8000)

    @patch("app.server.uvicorn.run")
    @patch("app.server.create_app")
    def test_start_requires_the_totp_key_before_creating_the_application(self, create_app, uvicorn_run) -> None:
        output = StringIO()

        with redirect_stdout(output):
            result = start(self.settings(totp_encryption_key=None))

        self.assertEqual(result, 1)
        self.assertIn("TOTP_ENCRYPTION_KEY must be defined", output.getvalue())
        create_app.assert_not_called()
        uvicorn_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
