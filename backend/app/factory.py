from fastapi import FastAPI

from app.infrastructure.persistence.sqlite.databases import SqliteDatabases
from app.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
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
    return application
