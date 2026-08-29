from typing import Annotated

from pydantic import Field


Icon = Annotated[str, Field(min_length=1, max_length=50)]
RgbColorCode = Annotated[bytes, Field(min_length=3, max_length=3)]
