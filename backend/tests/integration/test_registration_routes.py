import hashlib
import time
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi import HTTPException, Request
from pydantic import ValidationError

from app.api.registration import create_user, validate_invitation
from app.api.schema.registration import RegisterUserRequest, ValidateInvitationRequest
from app.application.registry.use_cases.user_invitation import create_user_invitation
from app.factory import create_app
from app.settings import Settings
from tests.fakes import FakePasswordHasher, FakeRateLimiter, FakeTotpAuthenticator


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
LEDGER_SCHEMA_PATH = ROOT / "app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"


class RegistrationRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        directory = Path(self.temporary_directory.name)
        settings = Settings(
            registry_schema_path=REGISTRY_SCHEMA_PATH,
            ledger_schema_path=LEDGER_SCHEMA_PATH,
            registry_db_path=directory / "registry/registry.sqlite",
            ledger_dbs_dir=directory / "ledgers",
            registration_validate_ip_rate_limit="7/minute",
            registration_create_ip_rate_limit="4/hour",
            password_hash_concurrency=3,
        )
        self.password_hasher = FakePasswordHasher()
        self.rate_limiter = FakeRateLimiter()
        self.application = create_app(settings, self.password_hasher, self.rate_limiter, FakeTotpAuthenticator())
        self.request = Request({"type": "http", "app": self.application, "client": ("192.0.2.1", 50000), "headers": []})

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def create_invitation(self):
        return create_user_invitation(self.application.state.databases.open_registry, int(time.time()), 3600)

    def test_validate_accepts_an_available_invitation_without_a_response_body(self) -> None:
        code = self.create_invitation()

        result = validate_invitation(ValidateInvitationRequest(invitation_code=code), self.request)

        self.assertIsNone(result)
        self.assertEqual(self.rate_limiter.checks, [("7/minute", "registration-validate-ip", "192.0.2.1")])

    def test_validate_is_exposed_as_no_content(self) -> None:
        responses = self.application.openapi()["paths"]["/api/registration/validate"]["post"]["responses"]

        self.assertIn("204", responses)
        self.assertNotIn("content", responses["204"])

    def test_validate_does_not_reveal_the_state_of_an_unavailable_invitation(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            validate_invitation(ValidateInvitationRequest(invitation_code="0" * 16), self.request)

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(raised.exception.detail, "Invitation not available")

    def test_request_models_reject_malformed_code_and_blank_name(self) -> None:
        with self.assertRaises(ValidationError):
            ValidateInvitationRequest(invitation_code="short")
        with self.assertRaises(ValidationError):
            RegisterUserRequest(invitation_code="0" * 16, name="   ", password="correct horse battery")

    def test_register_creates_user_without_starting_a_session(self) -> None:
        code = self.create_invitation()

        result = create_user(self.registration(code), self.request)

        self.assertIsNone(result)
        with self.application.state.databases.open_registry() as unit_of_work:
            user = unit_of_work.user_repository.get_by_normalized_name("alice")
            assert user is not None
            sessions = unit_of_work.auth_session_repository.list_by_user(user.uuid)
        self.assertEqual(user.password_hash, "$argon2id$test$correct horse battery")
        self.assertEqual(sessions, [])

    def test_register_applies_the_ip_limit(self) -> None:
        code = self.create_invitation()

        create_user(self.registration(code), self.request)

        self.assertEqual(self.rate_limiter.checks, [("4/hour", "registration-create-ip", "192.0.2.1")])

    def test_register_is_exposed_as_no_content(self) -> None:
        responses = self.application.openapi()["paths"]["/api/registration"]["post"]["responses"]

        self.assertIn("204", responses)
        self.assertNotIn("content", responses["204"])

    def test_register_rejects_when_password_hash_capacity_is_exhausted(self) -> None:
        code = self.create_invitation()
        semaphore = self.application.state.password_hash_semaphore
        for _ in range(self.application.state.settings.password_hash_concurrency):
            self.assertTrue(semaphore.acquire(blocking=False))
        try:
            with self.assertRaises(HTTPException) as raised:
                create_user(self.registration(code), self.request)
        finally:
            for _ in range(self.application.state.settings.password_hash_concurrency):
                semaphore.release()

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.headers, {"Retry-After": "1"})
        self.assertEqual(self.password_hasher.passwords, [])

    def test_rate_limit_rejects_registration_before_password_hashing(self) -> None:
        code = self.create_invitation()
        self.rate_limiter.rejected_namespace = "registration-create-ip"

        with self.assertRaises(HTTPException) as raised:
            create_user(self.registration(code), self.request)

        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(raised.exception.headers, {"Retry-After": "17"})
        self.assertEqual(self.password_hasher.passwords, [])

    def test_invalid_invitation_does_not_hash_the_password(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            create_user(self.registration("0" * 16), self.request)

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual([check[1] for check in self.rate_limiter.checks], ["registration-create-ip"])
        self.assertEqual(self.password_hasher.passwords, [])

    def test_existing_name_returns_conflict_without_consuming_second_invitation(self) -> None:
        first_code = self.create_invitation()
        second_code = self.create_invitation()
        with self.application.state.databases.open_registry() as unit_of_work:
            second_invitation = unit_of_work.user_invitation_repository.get_by_secret_hash(hashlib.sha256(second_code.encode("ascii")).digest())
        assert second_invitation is not None
        create_user(self.registration(first_code), self.request)
        payload = RegisterUserRequest(invitation_code=second_code, name="ＡLICE", password="another valid password")

        with self.assertRaises(HTTPException) as raised:
            create_user(payload, self.request)

        self.assertEqual(raised.exception.status_code, 409)
        with self.application.state.databases.open_registry() as unit_of_work:
            invitation = unit_of_work.user_invitation_repository.get(second_invitation.uuid)
        assert invitation is not None
        self.assertIsNone(invitation.consumed_at)

    @staticmethod
    def registration(invitation_code: str) -> RegisterUserRequest:
        return RegisterUserRequest(invitation_code=invitation_code, name="Alice", password="correct horse battery")


if __name__ == "__main__":
    unittest.main()
