from typing import Annotated

from pydantic import Field


TotpCode = Annotated[str, Field(min_length=6, max_length=6, pattern=r"^\d{6}$")]
