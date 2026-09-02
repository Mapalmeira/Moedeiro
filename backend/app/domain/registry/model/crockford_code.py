import base64
import secrets
from typing import Annotated

from pydantic import Field


CrockfordCode = Annotated[str, Field(min_length=16, max_length=16, pattern=r"^[0-9ABCDEFGHJKMNPQRSTVWXYZ]{16}$")]
CROCKFORD_TRANSLATION = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567", "0123456789ABCDEFGHJKMNPQRSTVWXYZ")


def generate_crockford_code(byte_count: int = 10) -> str:
    return base64.b32encode(secrets.token_bytes(byte_count)).decode("ascii").translate(CROCKFORD_TRANSLATION)
