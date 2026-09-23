import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.factory import create_app
from app.settings import Settings
from tests.fakes import FakeCredentialOperationExecutor, FakePasswordHasher, FakeRateLimiter, FakeTotpAuthenticator


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class ExternalAccessHttpTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        directory = Path(self.temporary_directory.name)
        self.password_hasher = FakePasswordHasher()
        self.rate_limiter = FakeRateLimiter()
        self.application = create_app(
            Settings(
                registry_schema_path=REGISTRY_SCHEMA_PATH,
                ledger_schema_path=LEDGER_SCHEMA_PATH,
                registry_db_path=directory / "registry/registry.sqlite",
                ledger_dbs_dir=directory / "ledgers",
                authenticated_user_operations_rate_limit="11/minute",
                external_access_operations_rate_limit="7/minute",
            ),
            self.password_hasher,
            self.rate_limiter,
            FakeTotpAuthenticator(),
            FakeCredentialOperationExecutor(),
            mount_frontend=False,
        )
        with self.application.state.databases.open_registry() as unit_of_work:
            self.user = unit_of_work.user_repository.create("Alice", self.password_hasher.hash("correct password"), 10)
            unit_of_work.commit()
        self.password_hasher.passwords.clear()
        self.client = TestClient(self.application, base_url="https://testserver")
        self.client.__enter__()
        self.assertEqual(
            self.client.post(
                "/api/authentication/login",
                json={"name": "Alice", "password": "correct password"},
            ).status_code,
            204,
        )
        ledger_response = self.client.post(
            "/api/ledgers",
            json={"name": "Household", "icon": "lucide:WalletCards", "color_code": "#102030"},
        )
        self.assertEqual(ledger_response.status_code, 201)
        self.ledger_uuid = ledger_response.json()["uuid"]

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.temporary_directory.cleanup()

    def create_external_access(self, name: str = "Sync plugin") -> dict:
        response = self.client.post(
            f"/api/ledgers/{self.ledger_uuid}/external-accesses",
            json={"name": name, "current_password": "correct password"},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def bearer_client(self, token: str) -> TestClient:
        return TestClient(
            self.application,
            base_url="https://testserver",
            headers={"Authorization": f"Bearer {token}"},
        )

    def test_management_api_is_session_only_and_token_is_returned_only_on_creation(self) -> None:
        with TestClient(self.application, base_url="https://testserver") as anonymous:
            self.assertEqual(anonymous.get(f"/api/ledgers/{self.ledger_uuid}/external-accesses").status_code, 401)

        response = self.client.post(
            f"/api/ledgers/{self.ledger_uuid}/external-accesses",
            json={"name": "Sync plugin", "current_password": "correct password"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers["cache-control"], "no-store")
        created = response.json()
        self.assertEqual(created["name"], "Sync plugin")
        self.assertTrue(created["token"])

        listed = self.client.get(f"/api/ledgers/{self.ledger_uuid}/external-accesses")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)
        self.assertEqual(listed.json()[0]["grant_uuid"], created["grant_uuid"])
        self.assertEqual(listed.json()[0]["external_access_uuid"], created["external_access_uuid"])
        self.assertNotIn("token", listed.json()[0])

        with self.bearer_client(created["token"]) as bearer_only:
            self.assertEqual(bearer_only.get("/api/ledgers").status_code, 401)
            self.assertEqual(bearer_only.get(f"/api/ledgers/{self.ledger_uuid}/external-accesses").status_code, 401)

    def test_creation_returns_conflict_when_external_access_limit_is_reached(self) -> None:
        with patch("app.application.registry.use_cases.grant.MAXIMUM_EXTERNAL_ACCESSES_PER_LEDGER", 1):
            self.create_external_access("First")
            response = self.client.post(
                f"/api/ledgers/{self.ledger_uuid}/external-accesses",
                json={"name": "Second", "current_password": "correct password"},
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json(), {"detail": "External access limit reached"})
        listed = self.client.get(f"/api/ledgers/{self.ledger_uuid}/external-accesses")
        self.assertEqual(len(listed.json()), 1)

    def test_external_access_cannot_delete_ledger(self) -> None:
        external = self.create_external_access()

        with self.bearer_client(external["token"]) as bearer_only:
            response = bearer_only.delete(f"/api/ledgers/{self.ledger_uuid}")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Invalid session"})
        ledger = self.client.get(f"/api/ledgers/{self.ledger_uuid}")
        self.assertEqual(ledger.status_code, 200)
        self.assertEqual(ledger.json()["uuid"], self.ledger_uuid)

    def test_management_creation_and_revocation_enforce_password_and_totp(self) -> None:
        with self.application.state.databases.open_registry() as unit_of_work:
            unit_of_work.mfa_method_repository.create(self.user.uuid, "TOTP", b"FAKESECRET", 10, 610, 10)
            unit_of_work.commit()

        wrong_password = self.client.post(
            f"/api/ledgers/{self.ledger_uuid}/external-accesses",
            json={"name": "Sync plugin", "current_password": "wrong password", "totp_code": "123456"},
        )
        self.assertEqual(wrong_password.status_code, 401)
        self.assertEqual(wrong_password.json(), {"detail": "Invalid current password"})

        missing_totp = self.client.post(
            f"/api/ledgers/{self.ledger_uuid}/external-accesses",
            json={"name": "Sync plugin", "current_password": "correct password"},
        )
        self.assertEqual(missing_totp.status_code, 401)
        self.assertEqual(missing_totp.json(), {"detail": "TOTP required"})

        created = self.client.post(
            f"/api/ledgers/{self.ledger_uuid}/external-accesses",
            json={"name": "Sync plugin", "current_password": "correct password", "totp_code": "123456"},
        )
        self.assertEqual(created.status_code, 201)

        missing_revoke_totp = self.client.request(
            "DELETE",
            f"/api/ledgers/{self.ledger_uuid}/external-accesses/{created.json()['grant_uuid']}",
            json={"current_password": "correct password"},
        )
        self.assertEqual(missing_revoke_totp.status_code, 401)
        self.assertEqual(missing_revoke_totp.json(), {"detail": "TOTP required"})

        revoked = self.client.request(
            "DELETE",
            f"/api/ledgers/{self.ledger_uuid}/external-accesses/{created.json()['grant_uuid']}",
            json={"current_password": "correct password", "totp_code": "123456"},
        )
        self.assertEqual(revoked.status_code, 204)

    def test_bearer_token_can_read_and_write_ledger_routes(self) -> None:
        external = self.create_external_access()
        with self.bearer_client(external["token"]) as client:
            currencies = client.get(f"/api/ledgers/{self.ledger_uuid}/currencies")
            self.assertEqual(currencies.status_code, 200)
            currency_uuid = currencies.json()[0]["uuid"]
            created = client.post(
                f"/api/ledgers/{self.ledger_uuid}/accounts",
                json={
                    "name": "External account",
                    "currency_uuid": currency_uuid,
                    "icon": "lucide:WalletCards",
                    "color_code": "#405060",
                },
            )
            self.assertEqual(created.status_code, 201)
            listed = client.get(f"/api/ledgers/{self.ledger_uuid}/accounts")
            self.assertEqual(listed.status_code, 200)
            self.assertIn("External account", [account["name"] for account in listed.json()])

        session_list = self.client.get(f"/api/ledgers/{self.ledger_uuid}/accounts")
        self.assertEqual(session_list.status_code, 200)
        self.assertIn("External account", [account["name"] for account in session_list.json()])

    def test_authorization_header_has_precedence_over_a_valid_session(self) -> None:
        response = self.client.get(
            f"/api/ledgers/{self.ledger_uuid}/accounts",
            headers={"Authorization": "Bearer invalid-token"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["www-authenticate"], "Bearer")
        self.assertEqual(response.json(), {"detail": "Invalid external access token"})

    def test_valid_token_cannot_access_an_ungranted_ledger_and_revocation_is_immediate(self) -> None:
        external = self.create_external_access()
        second = self.client.post(
            "/api/ledgers",
            json={"name": "Other", "icon": "lucide:WalletCards", "color_code": "#203040"},
        )
        self.assertEqual(second.status_code, 201)
        second_uuid = second.json()["uuid"]

        with self.bearer_client(external["token"]) as bearer:
            wrong_ledger = bearer.get(f"/api/ledgers/{second_uuid}/accounts")
        self.assertEqual(wrong_ledger.status_code, 404)
        self.assertEqual(wrong_ledger.json(), {"detail": "Ledger not found"})

        revoked = self.client.request(
            "DELETE",
            f"/api/ledgers/{self.ledger_uuid}/external-accesses/{external['grant_uuid']}",
            json={"current_password": "correct password"},
        )
        self.assertEqual(revoked.status_code, 204)

        with self.bearer_client(external["token"]) as bearer:
            after_revoke = bearer.get(f"/api/ledgers/{self.ledger_uuid}/accounts")
        self.assertEqual(after_revoke.status_code, 404)
        self.assertEqual(after_revoke.json(), {"detail": "Ledger not found"})

    def test_external_access_rate_limit_is_shared_across_external_accesses(self) -> None:
        first = self.create_external_access("First")
        second = self.create_external_access("Second")
        self.rate_limiter.checks.clear()

        with self.bearer_client(first["token"]) as first_client:
            self.assertEqual(first_client.get(f"/api/ledgers/{self.ledger_uuid}/accounts").status_code, 200)
        with self.bearer_client(second["token"]) as second_client:
            self.assertEqual(second_client.get(f"/api/ledgers/{self.ledger_uuid}/accounts").status_code, 200)
        self.assertEqual(self.client.get(f"/api/ledgers/{self.ledger_uuid}/accounts").status_code, 200)

        external_checks = [check for check in self.rate_limiter.checks if check[1] == "external-access-operations"]
        user_checks = [check for check in self.rate_limiter.checks if check[1] == "authenticated-user-operations"]
        self.assertEqual(
            external_checks,
            [
                ("7/minute", "external-access-operations", "external-accesses"),
                ("7/minute", "external-access-operations", "external-accesses"),
            ],
        )
        self.assertEqual(user_checks, [("11/minute", "authenticated-user-operations", str(self.user.uuid))])

    def test_external_rate_limit_rejection_does_not_fall_back_to_session(self) -> None:
        external = self.create_external_access()
        self.rate_limiter.rejected_namespace = "external-access-operations"

        response = self.client.get(
            f"/api/ledgers/{self.ledger_uuid}/accounts",
            headers={"Authorization": f"Bearer {external['token']}"},
        )

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["retry-after"], "17")

    def test_openapi_documents_external_bearer_authentication_and_one_time_token(self) -> None:
        schema = self.application.openapi()

        self.assertIn("External access token", schema["components"]["securitySchemes"])
        ledger_content_prefixes = (
            "/api/ledgers/{ledger_uuid}/accounts",
            "/api/ledgers/{ledger_uuid}/balances",
            "/api/ledgers/{ledger_uuid}/budgets",
            "/api/ledgers/{ledger_uuid}/cash-flow",
            "/api/ledgers/{ledger_uuid}/categories",
            "/api/ledgers/{ledger_uuid}/currencies",
            "/api/ledgers/{ledger_uuid}/events",
        )
        for path, operations in schema["paths"].items():
            if not path.startswith(ledger_content_prefixes):
                continue
            for method, operation in operations.items():
                if method == "parameters":
                    continue
                with self.subTest(path=path, method=method):
                    self.assertIn({"External access token": []}, operation["security"])

        self.assertNotIn("security", schema["paths"]["/api/ledgers/{ledger_uuid}/external-accesses"]["get"])
        security_description = schema["components"]["securitySchemes"]["External access token"]["description"]
        self.assertIn("specific to the ledger", security_description)
        self.assertIn("HTTPS", security_description)
        token_schema = schema["components"]["schemas"]["CreatedExternalAccessGrantResponse"]["properties"]["token"]
        self.assertIn("only once", token_schema["description"])
        self.assertIn("HTTPS", token_schema["description"])
