import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest

from fastapi import HTTPException, Request

from app.api.registry.routes.registration import create_user
from app.api.registry.schema.registration import RegisterUserRequest
from app.application.registry.use_cases.user_invitation import create_user_invitation
from app.factory import create_app
from app.settings import Settings
from tests.fakes import FakeCredentialOperationExecutor, FakeTotpAuthenticator


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class RegistrationSecurityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        directory = Path(self.temporary_directory.name)
        settings = Settings(
            registry_schema_path=REGISTRY_SCHEMA_PATH,
            ledger_schema_path=LEDGER_SCHEMA_PATH,
            registry_db_path=directory / "registry/registry.sqlite",
            ledger_dbs_dir=directory / "ledgers",
            registration_ip_attempts_rate_limit="2/hour",
        )
        self.application = create_app(settings, totp_authenticator=FakeTotpAuthenticator(), credential_operation_executor=FakeCredentialOperationExecutor(), mount_frontend=False)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def request(self, ip: str = "192.0.2.1") -> Request:
        return Request({"type": "http", "app": self.application, "client": (ip, 50000), "headers": []})

    def create_invitation(self) -> str:
        return create_user_invitation(self.application.state.databases.open_registry, int(time.time()), 3600)

    @staticmethod
    def registration(code: str, name: str, password: str = "correct horse battery") -> RegisterUserRequest:
        return RegisterUserRequest(invitation_code=code, name=name, password=password)

    def test_invalid_registration_attempts_exhaust_only_their_ip_limit(self) -> None:
        payload = self.registration("0" * 16, "Alice")

        for _ in range(2):
            with self.assertRaises(HTTPException) as unavailable:
                asyncio.run(create_user(payload, self.request()))
            self.assertEqual(unavailable.exception.status_code, 404)
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(create_user(payload, self.request()))

        self.assertEqual(raised.exception.status_code, 429)
        self.assertGreaterEqual(int(raised.exception.headers["Retry-After"]), 1)
        with self.assertRaises(HTTPException) as other_ip:
            asyncio.run(create_user(payload, self.request("198.51.100.1")))
        self.assertEqual(other_ip.exception.status_code, 404)
        with self.application.state.databases.open_registry() as unit_of_work:
            self.assertEqual(unit_of_work.user_repository.list_all("name", True), [])

    def test_registration_stores_a_hash_that_verifies_only_the_original_password(self) -> None:
        code = self.create_invitation()

        asyncio.run(create_user(self.registration(code, "Alice"), self.request()))

        with self.application.state.databases.open_registry() as unit_of_work:
            user = unit_of_work.user_repository.get_by_normalized_name("alice")
            assert user is not None
            sessions = unit_of_work.auth_session_repository.list_by_user(user.uuid)
        self.assertNotEqual(user.password_hash, "correct horse battery")
        self.assertTrue(self.application.state.password_hasher.verify(user.password_hash, "correct horse battery"))
        self.assertFalse(self.application.state.password_hasher.verify(user.password_hash, "wrong horse battery"))
        self.assertEqual(sessions, [])

    def test_equal_passwords_are_stored_as_different_hashes(self) -> None:
        asyncio.run(create_user(self.registration(self.create_invitation(), "Alice"), self.request()))
        asyncio.run(create_user(self.registration(self.create_invitation(), "Bob"), self.request()))

        with self.application.state.databases.open_registry() as unit_of_work:
            alice = unit_of_work.user_repository.get_by_normalized_name("alice")
            bob = unit_of_work.user_repository.get_by_normalized_name("bob")
        assert alice is not None
        assert bob is not None
        self.assertNotEqual(alice.password_hash, bob.password_hash)
        self.assertTrue(self.application.state.password_hasher.verify(alice.password_hash, "correct horse battery"))
        self.assertTrue(self.application.state.password_hasher.verify(bob.password_hash, "correct horse battery"))

    def test_consumed_invitation_cannot_register_another_user(self) -> None:
        code = self.create_invitation()
        asyncio.run(create_user(self.registration(code, "Alice"), self.request()))

        with self.assertRaises(HTTPException) as raised:
            asyncio.run(create_user(self.registration(code, "Bob"), self.request()))

        self.assertEqual(raised.exception.status_code, 404)
        with self.application.state.databases.open_registry() as unit_of_work:
            users = unit_of_work.user_repository.list_all("name", True)
        self.assertEqual([user.name for user in users], ["Alice"])


if __name__ == "__main__":
    unittest.main()
