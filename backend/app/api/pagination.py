from fastapi import HTTPException, Request, status


def validate_requested_page(request: Request, page_number: int, page_size: int) -> None:
    if page_number < 1:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="page_number must be greater than or equal to 1")
    if page_size < 1:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="page_size must be greater than or equal to 1")
    if page_size > request.app.state.settings.max_page_size:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"page_size must be less than or equal to {request.app.state.settings.max_page_size}")
