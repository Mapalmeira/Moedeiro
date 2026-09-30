import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app.factory import create_app
from app.settings import Settings
from tests.fakes import FakeCredentialOperationExecutor, FakeTotpAuthenticator


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class FrontendHttpTest(unittest.TestCase):
    def test_serves_the_frontend_and_falls_back_to_its_index_for_client_routes(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            frontend_directory = directory / "frontend"
            frontend_directory.mkdir()
            (frontend_directory / "index.html").write_text("<html>Moedeiro</html>")
            (frontend_directory / "main.js").write_text("console.log('moedeiro')")
            settings = Settings(
                registry_schema_path=REGISTRY_SCHEMA_PATH,
                ledger_schema_path=LEDGER_SCHEMA_PATH,
                registry_db_path=directory / "registry/registry.sqlite",
                ledger_dbs_dir=directory / "ledgers",
                frontend_dist_path=frontend_directory,
            )
            application = create_app(
                settings,
                totp_authenticator=FakeTotpAuthenticator(),
                credential_operation_executor=FakeCredentialOperationExecutor(),
                mount_frontend=True,
            )

            with TestClient(application) as client:
                index_response = client.get("/")
                javascript_response = client.get("/main.js")
                client_route_response = client.get("/home", headers={"Accept": "text/html"})

            self.assertEqual((index_response.status_code, index_response.text), (200, "<html>Moedeiro</html>"))
            self.assertEqual((javascript_response.status_code, javascript_response.text), (200, "console.log('moedeiro')"))
            self.assertEqual((client_route_response.status_code, client_route_response.text), (200, "<html>Moedeiro</html>"))
