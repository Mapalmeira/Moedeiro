import unicodedata


def normalize_search(value: str | None) -> str | None:
    if value is None:
        return None
    return "".join(character for character in unicodedata.normalize("NFD", value.casefold()) if not unicodedata.combining(character))


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
