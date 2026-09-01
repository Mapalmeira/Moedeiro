import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.application.registry.exceptions import InvalidCredentialsError, InvalidSessionError
from app.application.registry.use_cases.authentication import authenticate_session, login, logout, refresh_session
from app.domain.registry.model.auth_session import DEFAULT_ABSOLUTE_TIMEOUT_SECONDS, DEFAULT_INACTIVITY_TIMEOUT_SECONDS
from app.domain.registry.model.remember_session import DEFAULT_EXPIRATION_TIMEOUT_SECONDS
from app.infrastructure.persistence.sqlite.database import SqliteDatabase
from app.infrastructure.persistence.sqlite.registry.unit_of_work import SqliteRegistryUnitOfWork
from tests.fakes import FakePasswordHasher


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"


class AuthenticationUseCasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.database = SqliteDatabase.initialize(Path(self.temporary_directory.name) / "registry.sqlite", SCHEMA_PATH)
        self.password_hasher = FakePasswordHasher()
        with self.open_registry() as unit_of_work:
            self.user = unit_of_work.user_repository.create("Alice", self.password_hasher.hash("correct password"), 10)
            unit_of_work.commit()
        self.password_hasher.passwords.clear()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def open_registry(self) -> SqliteRegistryUnitOfWork:
        return SqliteRegistryUnitOfWork(self.database)

    def test_login_accepts_normalized_name_and_creates_short_and_remember_sessions(self) -> None:
        session_token, remember_token = login(self.open_registry, self.password_hasher, " ＡLICE ", "correct password", True, 20)

        assert remember_token is not None
        with self.open_registry() as unit_of_work:
            sessions = unit_of_work.auth_session_repository.list_by_user(self.user.uuid)
            remember_sessions = unit_of_work.remember_session_repository.list_by_user(self.user.uuid)
            stored_session = unit_of_work.auth_session_repository.get_by_token_hash(hashlib.sha256(session_token.encode("ascii")).digest())
            stored_remember_session = unit_of_work.remember_session_repository.get_by_token_hash(hashlib.sha256(remember_token.encode("ascii")).digest())
        self.assertEqual(len(sessions), 1)
        self.assertEqual(len(remember_sessions), 1)
        self.assertEqual(stored_session, sessions[0])
        self.assertEqual(stored_remember_session, remember_sessions[0])
        self.assertEqual(sessions[0].expires_at, 20 + DEFAULT_ABSOLUTE_TIMEOUT_SECONDS)
        self.assertEqual(sessions[0].inactivity_timeout_seconds, DEFAULT_INACTIVITY_TIMEOUT_SECONDS)
        self.assertEqual(remember_sessions[0].expires_at, 20 + DEFAULT_EXPIRATION_TIMEOUT_SECONDS)

    def test_login_without_remember_creates_only_the_short_session(self) -> None:
        _, remember_token = login(self.open_registry, self.password_hasher, "Alice", "correct password", False, 20)

        with self.open_registry() as unit_of_work:
            sessions = unit_of_work.auth_session_repository.list_by_user(self.user.uuid)
            remember_sessions = unit_of_work.remember_session_repository.list_by_user(self.user.uuid)
        self.assertIsNone(remember_token)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(remember_sessions, [])

    def test_new_login_revokes_sessions_presented_by_the_same_client(self) -> None:
        old_session_token, old_remember_token = login(self.open_registry, self.password_hasher, "Alice", "correct password", True, 20)
        assert old_remember_token is not None

        login(self.open_registry, self.password_hasher, "Alice", "correct password", False, 30, old_session_token, old_remember_token)

        with self.open_registry() as unit_of_work:
            sessions = unit_of_work.auth_session_repository.list_by_user(self.user.uuid)
            remember_sessions = unit_of_work.remember_session_repository.list_by_user(self.user.uuid)
        self.assertEqual(len(sessions), 2)
        self.assertCountEqual([session.revoked_at for session in sessions], [30, None])
        self.assertEqual(remember_sessions[0].revoked_at, 30)

    def test_login_rejects_unknown_user_and_wrong_password_without_creating_sessions(self) -> None:
        for name, password in (("Unknown", "correct password"), ("Alice", "wrong password")):
            with self.subTest(name=name, password=password):
                with self.assertRaises(InvalidCredentialsError):
                    login(self.open_registry, self.password_hasher, name, password, True, 20)

        with self.open_registry() as unit_of_work:
            self.assertEqual(unit_of_work.auth_session_repository.list_by_user(self.user.uuid), [])
            self.assertEqual(unit_of_work.remember_session_repository.list_by_user(self.user.uuid), [])

    def test_authenticate_returns_the_user_and_records_activity(self) -> None:
        session_token, _ = login(self.open_registry, self.password_hasher, "Alice", "correct password", False, 20)

        user = authenticate_session(self.open_registry, session_token, 30)

        with self.open_registry() as unit_of_work:
            sessions = unit_of_work.auth_session_repository.list_by_user(self.user.uuid)
        self.assertEqual(user, self.user)
        self.assertEqual(sessions[0].last_activity_at, 30)

    def test_authenticate_rejects_unknown_and_inactive_sessions(self) -> None:
        session_token, _ = login(self.open_registry, self.password_hasher, "Alice", "correct password", False, 20)

        with self.assertRaises(InvalidSessionError):
            authenticate_session(self.open_registry, "unknown", 30)
        with self.assertRaises(InvalidSessionError):
            authenticate_session(self.open_registry, "sessão-quebrada", 30)
        with self.assertRaises(InvalidSessionError):
            authenticate_session(self.open_registry, session_token, 20 + DEFAULT_INACTIVITY_TIMEOUT_SECONDS)

    def test_refresh_rotates_the_remember_token_and_creates_a_new_short_session(self) -> None:
        _, remember_token = login(self.open_registry, self.password_hasher, "Alice", "correct password", True, 20)
        assert remember_token is not None

        session_token, new_remember_token = refresh_session(self.open_registry, remember_token, 30)

        with self.open_registry() as unit_of_work:
            sessions = unit_of_work.auth_session_repository.list_by_user(self.user.uuid)
            old_remember = unit_of_work.remember_session_repository.get_by_token_hash(hashlib.sha256(remember_token.encode("ascii")).digest())
            new_remember = unit_of_work.remember_session_repository.get_by_token_hash(hashlib.sha256(new_remember_token.encode("ascii")).digest())
            new_session = unit_of_work.auth_session_repository.get_by_token_hash(hashlib.sha256(session_token.encode("ascii")).digest())
        self.assertEqual(len(sessions), 2)
        self.assertIsNone(old_remember)
        self.assertIsNotNone(new_remember)
        self.assertIsNotNone(new_session)
        assert new_remember is not None
        self.assertEqual(new_remember.expires_at, 20 + DEFAULT_EXPIRATION_TIMEOUT_SECONDS)
        with self.assertRaises(InvalidSessionError):
            refresh_session(self.open_registry, remember_token, 31)

    def test_refresh_rejects_an_expired_remember_session_without_creating_a_short_session(self) -> None:
        token = "remember-token"
        with self.open_registry() as unit_of_work:
            unit_of_work.remember_session_repository.create(self.user.uuid, hashlib.sha256(token.encode("ascii")).digest(), 20, 30)
            unit_of_work.commit()

        with self.assertRaises(InvalidSessionError):
            refresh_session(self.open_registry, token, 30)

        with self.open_registry() as unit_of_work:
            self.assertEqual(unit_of_work.auth_session_repository.list_by_user(self.user.uuid), [])

    def test_refresh_rejects_a_malformed_remember_token(self) -> None:
        with self.assertRaises(InvalidSessionError):
            refresh_session(self.open_registry, "sessão-quebrada", 30)

    def test_logout_revokes_presented_sessions_and_is_idempotent(self) -> None:
        session_token, remember_token = login(self.open_registry, self.password_hasher, "Alice", "correct password", True, 20)
        assert remember_token is not None

        logout(self.open_registry, session_token, remember_token, 30)
        logout(self.open_registry, session_token, remember_token, 31)

        with self.open_registry() as unit_of_work:
            session = unit_of_work.auth_session_repository.get_by_token_hash(hashlib.sha256(session_token.encode("ascii")).digest())
            remember_session = unit_of_work.remember_session_repository.get_by_token_hash(hashlib.sha256(remember_token.encode("ascii")).digest())
        assert session is not None
        assert remember_session is not None
        self.assertEqual(session.revoked_at, 30)
        self.assertEqual(remember_session.revoked_at, 30)

    def test_logout_ignores_malformed_tokens(self) -> None:
        logout(self.open_registry, "sessão-quebrada", "lembrança-quebrada", 30)


if __name__ == "__main__":
    unittest.main()
