import os
from collections.abc import Mapping
from ipaddress import IPv4Address, IPv6Address
from pathlib import Path
from typing import Self

from limits import parse
from pydantic import BaseModel, ConfigDict, Field, FilePath, field_validator, model_validator


_APP_ROOT = Path(__file__).resolve().parent
_PROJECT_ROOT = _APP_ROOT.parent.parent
_DEFAULT_REGISTRY_SCHEMA_PATH = _APP_ROOT / "infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
_DEFAULT_LEDGER_SCHEMA_PATH = _APP_ROOT / "infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"
_DEFAULT_REGISTRY_DB_PATH = _PROJECT_ROOT / "data/registry/registry.sqlite"
_DEFAULT_LEDGER_DBS_DIR = _PROJECT_ROOT / "data/ledgers"
_DEFAULT_FRONTEND_DIST_PATH = _PROJECT_ROOT / "frontend/dist/moedeiro/browser"


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    registry_schema_path: FilePath = _DEFAULT_REGISTRY_SCHEMA_PATH
    ledger_schema_path: FilePath = _DEFAULT_LEDGER_SCHEMA_PATH
    registry_db_path: Path = _DEFAULT_REGISTRY_DB_PATH
    ledger_dbs_dir: Path = _DEFAULT_LEDGER_DBS_DIR
    frontend_dist_path: Path = _DEFAULT_FRONTEND_DIST_PATH
    registration_ip_attempts_rate_limit: str = Field(default="10/hour", min_length=1)
    login_ip_attempts_rate_limit: str = Field(default="5/minute", min_length=1)
    password_recovery_ip_attempts_rate_limit: str = Field(default="10/hour", min_length=1)
    totp_setup_ip_attempts_rate_limit: str = Field(default="5/minute", min_length=1)
    refresh_ip_attempts_rate_limit: str = Field(default="10/minute", min_length=1)
    authenticated_user_operations_rate_limit: str = Field(default="80/minute", min_length=1)
    sync_route_concurrency: int = Field(default=40, gt=0)
    credential_operation_concurrency: int = Field(default=8, gt=0)
    password_hash_concurrency: int = Field(default=2, gt=0)
    max_page_size: int = Field(default=200, gt=0)
    max_query_points: int = Field(default=500, gt=0)
    trusted_proxy_ip: IPv4Address | IPv6Address | None = None
    allow_insecure_http: bool = False
    totp_encryption_key: str | None = None

    @field_validator("registration_ip_attempts_rate_limit", "login_ip_attempts_rate_limit", "password_recovery_ip_attempts_rate_limit", "totp_setup_ip_attempts_rate_limit", "refresh_ip_attempts_rate_limit", "authenticated_user_operations_rate_limit")
    @classmethod
    def validate_rate_limit(cls, value: str) -> str:
        if parse(value).amount <= 0:
            raise ValueError("rate limit amount must be positive")
        return value

    @model_validator(mode="after")
    def validate_data_paths(self) -> Self:
        if self.registry_db_path.exists() and not self.registry_db_path.is_file():
            raise ValueError("REGISTRY_DB_PATH must be a file path")
        if self.ledger_dbs_dir.exists() and not self.ledger_dbs_dir.is_dir():
            raise ValueError("LEDGER_DBS_DIR must be a directory path")
        return self

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> Self:
        source = os.environ if environment is None else environment
        values: dict[str, str] = {}

        path_variable_names = {
            "registry_db_path": "REGISTRY_DB_PATH",
            "ledger_dbs_dir": "LEDGER_DBS_DIR",
            "frontend_dist_path": "FRONTEND_DIST_PATH",
        }
        for field_name, variable_name in path_variable_names.items():
            if variable_name not in source:
                continue
            value = source[variable_name]
            if not value.strip():
                raise ValueError(f"{variable_name} must not be empty")
            values[field_name] = value

        optional_variable_names = {
            "registration_ip_attempts_rate_limit": "REGISTRATION_IP_ATTEMPTS_RATE_LIMIT",
            "login_ip_attempts_rate_limit": "LOGIN_IP_ATTEMPTS_RATE_LIMIT",
            "password_recovery_ip_attempts_rate_limit": "PASSWORD_RECOVERY_IP_ATTEMPTS_RATE_LIMIT",
            "totp_setup_ip_attempts_rate_limit": "TOTP_SETUP_IP_ATTEMPTS_RATE_LIMIT",
            "refresh_ip_attempts_rate_limit": "REFRESH_IP_ATTEMPTS_RATE_LIMIT",
            "authenticated_user_operations_rate_limit": "AUTHENTICATED_USER_OPERATIONS_RATE_LIMIT",
            "sync_route_concurrency": "SYNC_ROUTE_CONCURRENCY",
            "credential_operation_concurrency": "CREDENTIAL_OPERATION_CONCURRENCY",
            "password_hash_concurrency": "PASSWORD_HASH_CONCURRENCY",
            "max_page_size": "MAX_PAGE_SIZE",
            "max_query_points": "MAX_QUERY_POINTS",
            "trusted_proxy_ip": "TRUSTED_PROXY_IP",
            "allow_insecure_http": "ALLOW_INSECURE_HTTP",
            "totp_encryption_key": "TOTP_ENCRYPTION_KEY",
        }
        for field_name, variable_name in optional_variable_names.items():
            if variable_name in source:
                values[field_name] = source[variable_name]

        trusted_proxy_ip = source.get("TRUSTED_PROXY_IP")
        if trusted_proxy_ip is not None:
            if trusted_proxy_ip.strip():
                values["trusted_proxy_ip"] = trusted_proxy_ip
            else:
                values.pop("trusted_proxy_ip", None)
        return cls.model_validate(values)
