from threading import BoundedSemaphore

from fastapi import FastAPI

from app.application.services.password_hasher import PasswordHasher
from app.application.services.rate_limiter import RateLimiter
from app.infrastructure.persistence.sqlite.databases import SqliteDatabases
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
    application.state.password_hash_semaphore = BoundedSemaphore(2)
    application.state.rate_limiter = RateLimiter() if rate_limiter is None else rate_limiter
    return application


def _create_password_hasher() -> PasswordHasher:
    from argon2 import PasswordHasher as Argon2PasswordHasher

    return Argon2PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1, hash_len=32, salt_len=16)
