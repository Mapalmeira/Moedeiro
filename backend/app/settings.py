import os
from collections.abc import Mapping
from pathlib import Path
from typing import Self

from limits import parse
from pydantic import BaseModel, ConfigDict, Field, FilePath, field_validator, model_validator


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    registry_schema_path: FilePath
    ledger_schema_path: FilePath
    registry_db_path: Path
    ledger_dbs_dir: Path
    registration_validate_rate_limit: str = Field(default="5/minute", min_length=1)
    registration_create_ip_rate_limit: str = Field(default="5/hour", min_length=1)
    password_hash_concurrency: int = Field(default=2, gt=0)

    @field_validator("registration_validate_rate_limit", "registration_create_ip_rate_limit")
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
        variable_names = {
            "registry_schema_path": "REGISTRY_SCHEMA_PATH",
            "ledger_schema_path": "LEDGER_SCHEMA_PATH",
            "registry_db_path": "REGISTRY_DB_PATH",
            "ledger_dbs_dir": "LEDGER_DBS_DIR",
        }
        values: dict[str, str] = {}
        for field_name, variable_name in variable_names.items():
            value = source.get(variable_name)
            if value is None or not value.strip():
                raise ValueError(f"{variable_name} must be defined")
            values[field_name] = value
        optional_variable_names = {
            "registration_validate_rate_limit": "REGISTRATION_VALIDATE_RATE_LIMIT",
            "registration_create_ip_rate_limit": "REGISTRATION_CREATE_IP_RATE_LIMIT",
            "password_hash_concurrency": "PASSWORD_HASH_CONCURRENCY",
        }
        for field_name, variable_name in optional_variable_names.items():
            if variable_name in source:
                values[field_name] = source[variable_name]
        return cls.model_validate(values)
