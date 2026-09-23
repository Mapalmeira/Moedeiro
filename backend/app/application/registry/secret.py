import hashlib
import secrets


OPAQUE_TOKEN_BYTE_COUNT = 32


def generate_opaque_token() -> tuple[str, bytes]:
    token = secrets.token_urlsafe(OPAQUE_TOKEN_BYTE_COUNT)
    return token, hash_ascii_secret(token)


def hash_ascii_secret(secret: str) -> bytes:
    return hashlib.sha256(secret.encode("ascii")).digest()


def try_hash_ascii_secret(secret: str) -> bytes | None:
    try:
        return hash_ascii_secret(secret)
    except UnicodeEncodeError:
        return None
