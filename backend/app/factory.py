from threading import BoundedSemaphore

from fastapi import FastAPI

from app.api.authentication import router as authentication_router
from app.api.password import router as password_router
from app.api.registration import router as registration_router
from app.application.registry.password_hasher import PasswordHasher
from app.infrastructure.persistence.sqlite.databases import SqliteDatabases
from app.infrastructure.security.rate_limiter import RateLimiter
from app.settings import Settings


def create_app(settings: Settings | None = None, password_hasher: PasswordHasher | None = None, rate_limiter: RateLimiter | None = None) -> FastAPI:
    selected_settings = Settings.from_environment() if settings is None else settings
    databases = SqliteDatabases(
        selected_settings.registry_db_path,
        selected_settings.registry_schema_path,
        selected_settings.ledger_dbs_dir,
        selected_settings.ledger_schema_path,
    )
    databases.initialize()

    application = FastAPI(title="Moedeiro")
    application.state.settings = selected_settings
    application.state.databases = databases
    application.state.password_hasher = _create_password_hasher() if password_hasher is None else password_hasher
    application.state.password_hash_semaphore = BoundedSemaphore(selected_settings.password_hash_concurrency)
    application.state.rate_limiter = RateLimiter() if rate_limiter is None else rate_limiter
    application.include_router(authentication_router)
    application.include_router(password_router)
    application.include_router(registration_router)
    return application


def _create_password_hasher() -> PasswordHasher:
    from app.infrastructure.security.password_hasher import Argon2PasswordHasher

    return Argon2PasswordHasher()
