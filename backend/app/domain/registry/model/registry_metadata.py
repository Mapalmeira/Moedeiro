from pydantic import BaseModel, Field


class RegistryMetadata(BaseModel):
    schema_version: int = Field(ge=1)
