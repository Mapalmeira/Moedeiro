import re
from typing import Annotated

from pydantic import AfterValidator, Field


ICON_MAX_LENGTH = 100
UNICODE_ICON_PREFIX = "unicode:"
LUCIDE_ICON_PREFIX = "lucide:"
_LUCIDE_ICON_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")


def validate_icon(value: str) -> str:
    if value.startswith(UNICODE_ICON_PREFIX):
        content = value.removeprefix(UNICODE_ICON_PREFIX)
        if not 1 <= len(content) <= 3:
            raise ValueError("unicode icon must contain between 1 and 3 characters")
        return value

    if value.startswith(LUCIDE_ICON_PREFIX):
        name = value.removeprefix(LUCIDE_ICON_PREFIX)
        if not _LUCIDE_ICON_NAME_PATTERN.fullmatch(name):
            raise ValueError("invalid Lucide icon name")
        return value

    raise ValueError("icon must start with unicode: or lucide:")


Icon = Annotated[str, Field(min_length=1, max_length=ICON_MAX_LENGTH), AfterValidator(validate_icon)]
RgbColorCode = Annotated[bytes, Field(min_length=3, max_length=3)]
