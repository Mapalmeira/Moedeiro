from fastapi import APIRouter, status


router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_204_NO_CONTENT)
def health_check() -> None:
    pass
