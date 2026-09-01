from typing import Annotated

from pydantic import Field


CrockfordCode = Annotated[str, Field(min_length=16, max_length=16, pattern=r"^[0-9ABCDEFGHJKMNPQRSTVWXYZ]{16}$")]
