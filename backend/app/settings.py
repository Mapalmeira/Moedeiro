import os
from collections.abc import Mapping
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, FilePath, model_validator


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    registry_schema_path: FilePath
    ledger_schema_path: FilePath
    registry_db_path: Path
    ledger_dbs_dir: Path

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
        return cls.model_validate(values)
