import uvicorn

from app.factory import create_app
from app.settings import Settings


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def start(settings: Settings, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, mount_frontend: bool = True) -> int:
    if settings.totp_encryption_key is None:
        print("TOTP_ENCRYPTION_KEY must be defined")
        return 1

    application = create_app(settings=settings, mount_frontend=mount_frontend)
    uvicorn.run(application, host=host, port=port)
    return 0
