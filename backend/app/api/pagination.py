from fastapi import HTTPException, Request, status

from app.pagination import validate_page


def validate_requested_page(request: Request, page_number: int, page_size: int) -> None:
    try:
        validate_page(page_number, page_size, request.app.state.settings.max_page_size)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
