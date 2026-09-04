from contextlib import asynccontextmanager
from threading import BoundedSemaphore
from typing import AsyncGenerator

from anyio.to_thread import current_default_thread_limiter
from fastapi import FastAPI

from app.api.ledger.routes.account import router as account_router
from app.api.ledger.routes.budget import router as budget_router
from app.api.ledger.routes.category import router as category_router
from app.api.ledger.routes.currency import router as currency_router
from app.api.ledger.routes.financial_event import router as financial_event_router
from app.api.registry.routes.authentication import router as authentication_router
from app.api.registry.routes.ledger import router as ledger_router
from app.api.registry.routes.password import router as password_router
from app.api.registry.routes.registration import router as registration_router
from app.api.registry.routes.totp import router as totp_router
from app.application.registry.password_hasher import PasswordHasher
from app.application.registry.totp_authenticator import TotpAuthenticator
from app.infrastructure.concurrency.concurrent_password_hasher import ConcurrentPasswordHasher
from app.infrastructure.concurrency.credential_operation_executor import CredentialOperationExecutor
from app.infrastructure.persistence.sqlite.databases import SqliteDatabases
from app.infrastructure.security.rate_limiter import RateLimiter
from app.settings import Settings


def create_app(settings: Settings | None = None, password_hasher: PasswordHasher | None = None, rate_limiter: RateLimiter | None = None, totp_authenticator: TotpAuthenticator | None = None, credential_operation_executor: CredentialOperationExecutor | None = None) -> FastAPI:
    selected_settings = Settings.from_environment() if settings is None else settings
    databases = SqliteDatabases(
        selected_settings.registry_db_path,
        selected_settings.registry_schema_path,
        selected_settings.ledger_dbs_dir,
        selected_settings.ledger_schema_path,
    )
    databases.initialize()

    application = FastAPI(title="Moedeiro", lifespan=_lifespan)
    application.state.settings = selected_settings
    application.state.databases = databases
    password_hash_semaphore = BoundedSemaphore(selected_settings.password_hash_concurrency)
    selected_password_hasher = _create_password_hasher() if password_hasher is None else password_hasher
    application.state.password_hasher = ConcurrentPasswordHasher(selected_password_hasher, password_hash_semaphore)
    application.state.totp_authenticator = _create_totp_authenticator(selected_settings) if totp_authenticator is None else totp_authenticator
    application.state.password_hash_semaphore = password_hash_semaphore
    application.state.credential_operation_executor = CredentialOperationExecutor(selected_settings.credential_operation_concurrency) if credential_operation_executor is None else credential_operation_executor
    application.state.rate_limiter = RateLimiter() if rate_limiter is None else rate_limiter
    application.include_router(account_router)
    application.include_router(authentication_router)
    application.include_router(budget_router)
    application.include_router(category_router)
    application.include_router(currency_router)
    application.include_router(financial_event_router)
    application.include_router(ledger_router)
    application.include_router(password_router)
    application.include_router(registration_router)
    application.include_router(totp_router)
    return application


@asynccontextmanager
async def _lifespan(application: FastAPI) -> AsyncGenerator[None]:
    current_default_thread_limiter().total_tokens = application.state.settings.sync_route_concurrency
    try:
        yield
    finally:
        application.state.credential_operation_executor.shutdown()


def _create_password_hasher() -> PasswordHasher:
    from app.infrastructure.security.password_hasher import Argon2PasswordHasher

    return Argon2PasswordHasher()


def _create_totp_authenticator(settings: Settings) -> TotpAuthenticator:
    if settings.totp_encryption_key is None:
        raise ValueError("TOTP_ENCRYPTION_KEY must be defined")
    from app.infrastructure.security.totp_authenticator import FernetTotpAuthenticator

    return FernetTotpAuthenticator(settings.totp_encryption_key)
